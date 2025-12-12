from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from app.common.models import orm
from app.common.models.enums import DialogStatus
from app.common.utils.functions import (
    generate_message,
    normalize_dashes,
    randomize_message,
)
from app.common.utils.prompt import (
    build_prompt,
    get_ooc_status,
    get_status_addon,
    strip_ooc_status,
)
from app.config import config
from app.dto.chat import ChatIn, ChatOut, MessageRole
from app.routers.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


params = {
    "api_key": config.openai.api_key,
    "timeout": config.openai.timeout,
}
if config.openai.base_url:
    params["base_url"] = config.openai.base_url


client = AsyncOpenAI(**params)


@router.post("/", response_model=ChatOut)
async def chat(chat: ChatIn, user=Depends(get_current_user)):
    project = await orm.Project.filter(
        id=chat.project_id, user_id=user.id
    ).get_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    STATUS_ADDON = await get_status_addon()

    if not chat.messages and project.first_message:
        first_message = generate_message(project.first_message)
        first_message = randomize_message(first_message)
        return ChatOut(text=first_message, status=chat.status)
    else:
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                msg.text = f"{msg.text}\n{STATUS_ADDON}"
                if chat.status == DialogStatus.CLOSING:
                    msg.text += "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"

                break

    orm_prompt = await orm.Prompt.get(project_id=project.id)
    prompt = await build_prompt(orm_prompt.to_dict(), chat.status)

    messages = [{"role": "system", "content": prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    raw_response = await client.responses.create(
        model="gpt-5.1-codex-mini",  # config.openai.model,  # например "gpt-4.1" или "gpt-3.5-turbo"
        input=cast(Any, messages),
    )

    response = raw_response.output_text  # completion.choices[0].message.content or ""

    add_status_alert = False
    status = get_ooc_status(response)
    if not status:
        add_status_alert = True
        status = chat.status

    response = strip_ooc_status(response)
    response = normalize_dashes(response)

    if add_status_alert:
        response += "\n\nВНИМАНИЕ!! AI НЕ ВЕРНУЛ СТАТУС"
    return ChatOut(text=response, status=status)
