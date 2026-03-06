import re
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException

from app.common.models import orm
from app.common.models.enums import DialogStatus
from app.common.utils import openrouter
from app.common.utils.functions import (
    generate_message,
    normalize_dashes,
    randomize_message,
)
from app.common.utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    analyze_dialog_status,
    build_prompt_v2,
    get_active_status,
    get_status_addon,
)
from app.dto.chat import ChatIn, ChatOut, Message, MessageRole
from app.dto.project import ProjectSkipOptions
from app.routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatOut)
async def chat(chat: ChatIn, user=Depends(get_current_user)):
    project = await orm.Project.filter(
        id=chat.project_id, user_id=user.id
    ).get_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    skip_options = (
        ProjectSkipOptions(**project.skip_options)
        if project.skip_options
        else DEFAULT_SKIP_OPTIONS
    )
    # TODO - сделать оповещение если статус не найден и оставлен предыдущий
    if chat.messages:
        new_status = await analyze_dialog_status(
            user,
            [{"role": m.role.value, "content": m.text} for m in chat.messages],
            chat.status,
        )
        if not new_status:
            raise HTTPException(
                status_code=404, detail="Не могу определить статус диалога"
            )

        chat.status = get_active_status(new_status, skip_options)

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
        STATUS_ADDON = await get_status_addon()
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                msg.text = f"{msg.text}\n{STATUS_ADDON}"
                if chat.status == DialogStatus.CLOSING:
                    msg.text += "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"

                break

    orm_prompt = await orm.Prompt.get(project_id=project.id)

    prompt = build_prompt_v2(orm_prompt.to_dict(), chat.status)

    messages = [{"role": "system", "content": prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    try:
        response = await openrouter.create_response(user, messages)
    except Exception as e:
        return ChatOut(text=str(e), status=chat.status)

    if not response:
        return ChatOut(text="AI не вернул ответ", status=chat.status)

    response = normalize_dashes(response)

    return ChatOut(text=response, status=chat.status)
