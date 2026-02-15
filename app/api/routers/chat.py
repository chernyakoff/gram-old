from fastapi import APIRouter, Depends, HTTPException

from models import orm
from models.orm import DialogStatus
from utils import openrouter
from utils.functions import (
    generate_message,
    normalize_dashes,
    randomize_message,
)
from utils.openrouter import retrieve_chunks
from utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    ProjectSkipOptions,
    analyze_dialog_status,
    build_prompt_v2,
    get_active_status,
    get_calendar_addon,
    get_status_addon,
    validate_prompt,
)
from utils.schedule import TOOLS, ToolContext
from api.dto.chat import ChatIn, ChatOut, MessageRole, ToolEvent
from api.routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

def _render_tool_events_for_chat(tool_events: list[dict]) -> str:
    """
    Human-readable tool output for the test chat UI.
    This is intentionally explicit so it doesn't look like an assistant message.
    """
    import json

    if not tool_events:
        return ""

    lines: list[str] = []
    lines.append("=== TOOL OUTPUT (test chat) ===")
    for idx, ev in enumerate(tool_events, 1):
        tool = ev.get("tool", "unknown_tool")
        args = ev.get("arguments", {}) or {}
        result = ev.get("result", None)

        # Avoid dumping extremely long slot lists into the chat UI.
        if isinstance(result, dict) and isinstance(result.get("slots"), list):
            slots = result.get("slots") or []
            if len(slots) > 30:
                result = {
                    **result,
                    "slots": slots[:30],
                    "truncated": True,
                    "total_slots": len(slots),
                }

        lines.append(f"{idx}. {tool}")
        lines.append(f"args: {json.dumps(args, ensure_ascii=False)}")
        lines.append("result:")
        lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    lines.append("=== END TOOL OUTPUT ===")
    return "\n".join(lines)


@router.post("/", response_model=ChatOut)
async def chat(chat: ChatIn, user=Depends(get_current_user)):
    project = await orm.Project.filter(
        id=chat.project_id, user_id=user.id
    ).get_or_none()

    # chat.messages = [m for m in chat.messages if not m.text.startswith("FILES")]

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    orm_prompt = await orm.Prompt.get_or_none(project_id=project.id)
    skip_options = (
        ProjectSkipOptions(**project.skip_options)
        if project.skip_options
        else DEFAULT_SKIP_OPTIONS
    )

    if not validate_prompt(orm_prompt, project.skip_options):
        return ChatOut(text="В проекте отсутсвует промпт", status=chat.status)

    if not project.first_message:
        return ChatOut(
            text="В проекте отсутсвует первое сообщение", status=chat.status
        )

    status_changed = False

    # TODO - сделать оповещение если статус не найден и оставлен предыдущий
    if chat.messages:
        new_status = await analyze_dialog_status(
            user,
            [{"role": m.role.value, "content": m.text} for m in chat.messages],
            chat.status,
        )
        if not new_status:
            return ChatOut(text="Не могу определить статус диалога", status=chat.status)
            """ raise HTTPException(
                status_code=404, detail="Не могу определить статус диалога"
            ) """

        new_status = get_active_status(new_status, skip_options)
        if new_status != chat.status:
            status_changed = True
        chat.status = new_status

    if chat.status in [
        DialogStatus.COMPLETE,
        DialogStatus.NEGATIVE,
        DialogStatus.OPERATOR,
    ]:
        return ChatOut(text="ДИАЛОГ ЗАКРЫТ", status=chat.status)

    if not chat.messages and project.first_message:
        first_message = generate_message(project.first_message)
        first_message = randomize_message(first_message)
        return ChatOut(text=first_message, status=chat.status)
    else:
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                STATUS_ADDON = await get_status_addon()
                msg.text = f"{msg.text}\n{STATUS_ADDON}"
                if project.use_calendar:
                    CALENDAR_ADDON = await get_calendar_addon(user)
                    msg.text = f"\n\n{CALENDAR_ADDON}"
                if chat.status == DialogStatus.CLOSING:
                    msg.text += "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"

                break

    file_message = []
    if status_changed:
        files = await orm.ProjectFile.filter(project_id=project.id, status=chat.status)
        if files:
            file_message = ["Отправляю вам файлы"]
            for f in files:
                file_message.append(f.filename)

    prompt = build_prompt_v2(orm_prompt.to_dict(), chat.status)  # type: ignore

    chunks = []
    if await orm.ProjectDocument.filter(project_id=chat.project_id).count() > 0:
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                chunks = await retrieve_chunks(user, msg.text)

    if chunks:
        prompt = f"""
            {prompt}

            Используй следующий контекст для ответа на вопрос:

            {"\n".join(chunks)}
        """

    messages = [{"role": "system", "content": prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    tool_events: list[dict] = []
    if project.use_calendar:
        ctx = ToolContext(user, None)
        tool_handlers = {
            "get_slots": ctx.get_slots,
            "book_slot": ctx.book_slot,
            "cancel_meeting": ctx.cancel_meeting,
        }

        try:
            response = await openrouter.create_response_with_tools(
                user, messages, TOOLS, tool_handlers, tool_events=tool_events
            )
        except Exception as e:
            return ChatOut(text=str(e), status=chat.status)
    else:
        try:
            response = await openrouter.create_response(user, messages)
        except Exception as e:
            return ChatOut(text=str(e), status=chat.status)

    if not response:
        return ChatOut(text="AI не вернул ответ", status=chat.status)

    response = normalize_dashes(response)  # type: ignore

    if file_message:
        response = f"{'\n'.join(file_message)}\n\n{response}"

    # In the test chat, also show tool outputs in-band and via a structured field.
    if tool_events:
        tool_block = _render_tool_events_for_chat(tool_events)
        response = f"{tool_block}\n\n{response}"

    return ChatOut(
        text=response,
        status=chat.status,
        tool_events=[ToolEvent(**ev) for ev in tool_events] if tool_events else None,
    )
