import logging
import random

from fastapi import APIRouter, Depends, HTTPException

from api.dto.chat import ChatIn, ChatOut, MessageRole, ToolEvent
from api.routers.auth import get_current_user
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
    get_name_addon,
    get_status_addon,
    validate_prompt,
)
from utils.schedule import TOOLS, ToolContext

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {
    DialogStatus.COMPLETE,
    DialogStatus.NEGATIVE,
    DialogStatus.OPERATOR,
}

# In-memory cache for the prompt test UI: keep a stable random pair across turns.
# Keyed by (user_id, project_id) to avoid changing names every message.
_TEST_NAME_PAIR_CACHE: dict[tuple[int, int], tuple[int, int]] = {}


async def _get_test_name_addon(
    user: orm.User, project: orm.Project
) -> tuple[str, dict | None]:
    """
    Pick a random (Account, Recipient) for this user/project and produce get_name_addon().
    Returns (addon_text, tool_event_dict_or_None).
    """

    cache_key = (user.id, project.id)
    cached = _TEST_NAME_PAIR_CACHE.get(cache_key)

    async def _resolve_pair(account_id: int, recipient_id: int):
        account = await orm.Account.get_or_none(id=account_id, user_id=user.id)
        recipient = (
            await orm.Recipient.filter(id=recipient_id, mailing__user_id=user.id)
            .prefetch_related("mailing")
            .first()
        )
        if not account or not recipient:
            return None, None
        return account, recipient

    account: orm.Account | None = None
    recipient: orm.Recipient | None = None
    if cached:
        account, recipient = await _resolve_pair(cached[0], cached[1])
        if not account or not recipient:
            _TEST_NAME_PAIR_CACHE.pop(cache_key, None)

    if not account or not recipient:
        account_ids = await orm.Account.filter(
            user_id=user.id,
            project_id=project.id,
        ).values_list("id", flat=True)
        if not account_ids:
            account_ids = await orm.Account.filter(user_id=user.id).values_list(
                "id", flat=True
            )

        recipient_ids = await orm.Recipient.filter(
            mailing__user_id=user.id,
            mailing__project_id=project.id,
        ).values_list("id", flat=True)
        if not recipient_ids:
            recipient_ids = await orm.Recipient.filter(
                mailing__user_id=user.id
            ).values_list("id", flat=True)

        if not account_ids or not recipient_ids:
            return "", None

        picked_account_id = random.choice(list(account_ids))
        picked_recipient_id = random.choice(list(recipient_ids))
        _TEST_NAME_PAIR_CACHE[cache_key] = (picked_account_id, picked_recipient_id)
        account, recipient = await _resolve_pair(picked_account_id, picked_recipient_id)
        if not account or not recipient:
            return "", None

    addon = get_name_addon(account, recipient).strip()
    if not addon:
        return "", None

    tool_event = {
        "tool": "name_addon",
        "arguments": {
            "account_id": account.id,
            "recipient_id": recipient.id,
            "account_username": account.username,
            "recipient_username": recipient.username,
        },
        "result": addon,
    }
    return addon, tool_event


def _render_tool_events_for_chat(tool_events: list[dict]) -> str:
    """
    Human-readable tool output for the test chat UI.
    This is intentionally explicit so it doesn't look like an assistant message.
    """
    import json
    from datetime import date as date_cls
    from datetime import datetime

    if not tool_events:
        return ""

    def _format_iso_dt_strings(v):
        """
        Recursively format ISO-8601 date/datetime strings for display.
        Also formats slot_key-like strings: "<id>__<iso_dt>__<iso_dt>".
        """

        def _try_parse(s: str):
            s2 = s.strip()
            # Format slot_key-like strings too.
            if "__" in s2:
                parts = s2.split("__", 2)
                if len(parts) == 3 and parts[0].isdigit():
                    a = _try_parse(parts[1])
                    b = _try_parse(parts[2])
                    if isinstance(a, datetime) and isinstance(b, datetime):
                        return f"{parts[0]}__{a.strftime('%d.%m.%y %H:%M')}__{b.strftime('%d.%m.%y %H:%M')}"

            # Support "Z" suffix.
            if s2.endswith("Z") and "T" in s2:
                s2 = s2[:-1] + "+00:00"
            try:
                if "T" in s2 or ":" in s2:
                    return datetime.fromisoformat(s2)
            except ValueError:
                pass
            try:
                # Date-only tool args are common (YYYY-MM-DD).
                if len(s2) == 10 and s2[4] == "-" and s2[7] == "-":
                    return date_cls.fromisoformat(s2)
            except ValueError:
                pass
            return None

        if isinstance(v, dict):
            return {k: _format_iso_dt_strings(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_format_iso_dt_strings(val) for val in v]
        if isinstance(v, str):
            parsed = _try_parse(v)
            if isinstance(parsed, str):
                return parsed
            if isinstance(parsed, datetime):
                return parsed.strftime("%d.%m.%y %H:%M")
            if isinstance(parsed, date_cls):
                return parsed.strftime("%d.%m.%y")
            return v
        return v

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
        lines.append(
            f"args: {json.dumps(_format_iso_dt_strings(args), ensure_ascii=False)}"
        )
        lines.append("result:")
        lines.append(
            json.dumps(_format_iso_dt_strings(result), ensure_ascii=False, indent=2)
        )
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
        return ChatOut(text="В проекте отсутсвует первое сообщение", status=chat.status)

    # If the client already has a terminal status from a previous turn,
    # consider the dialog closed and don't call the model again.
    # If the status becomes terminal during this request, we still let the model
    # produce the final reply (same as in the Telegram task).
    if chat.status in TERMINAL_STATUSES:
        return ChatOut(text="ДИАЛОГ ЗАКРЫТ", status=chat.status)

    status_changed = False
    warnings: list[str] = []
    tool_events: list[dict] = []

    # TODO - сделать оповещение если статус не найден и оставлен предыдущий
    if chat.messages:
        new_status = await analyze_dialog_status(
            user,
            [{"role": m.role.value, "content": m.text} for m in chat.messages],
            chat.status,
        )
        if not new_status:
            # Match production behavior (Telegram task): keep previous status and continue.
            logger.warning(
                "Test chat: AI did not return dialog status; keeping previous"
            )
            warnings.append(
                f"AI не вернул статус диалога, оставлен предыдущий: {chat.status.value}"
            )
        else:
            new_status = get_active_status(new_status, skip_options)
            if new_status != chat.status:
                status_changed = True
            chat.status = new_status

    if not chat.messages and project.first_message:
        first_message = generate_message(project.first_message)
        first_message = randomize_message(first_message)
        return ChatOut(
            text=first_message, status=chat.status, warnings=warnings or None
        )
    else:
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                name_addon, name_ev = await _get_test_name_addon(user, project)
                if name_addon:
                    msg.text = f"{msg.text}\n{name_addon}"
                    if name_ev:
                        tool_events.append(name_ev)

                STATUS_ADDON = await get_status_addon()
                msg.text = f"{msg.text}\n{STATUS_ADDON}"
                if project.use_calendar:
                    CALENDAR_ADDON = await get_calendar_addon(user)
                    # Append calendar instructions; do not overwrite the user's message.
                    msg.text = f"{msg.text}\n\n{CALENDAR_ADDON}"

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
            return ChatOut(text=str(e), status=chat.status, warnings=warnings or None)
    else:
        try:
            response = await openrouter.create_response(user, messages)
        except Exception as e:
            return ChatOut(text=str(e), status=chat.status, warnings=warnings or None)

    if not response:
        return ChatOut(
            text="AI не вернул ответ", status=chat.status, warnings=warnings or None
        )

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
        warnings=warnings or None,
    )
