from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from app.cli.dev import build_prompt
from app.common.models import orm
from app.common.models.enums import DialogStatus
from app.common.utils.functions import generate_message
from app.common.utils.prompt import (
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

    # если сообщений нет, это первый вызов — просто возвращаем first_message

    if not chat.messages and project.first_message:
        first_message = generate_message(project.first_message)
        return ChatOut(text=first_message, status=chat.status)
    else:
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                msg.text = f"{msg.text}\n{get_status_addon(chat.status)}"
                if chat.status == DialogStatus.CLOSING:
                    msg.text += "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"

                print(f"QUESTION=====\n{msg.text}\n====")

                break

    prompt = await build_prompt(project.prompt, chat.status)

    # print("PROMPT", prompt)

    # иначе строим контекст для модели
    messages = [{"role": "system", "content": prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    completion = await client.chat.completions.create(
        model=config.openai.model,
        messages=messages,  # type: ignore
    )

    response = completion.choices[0].message.content or ""

    print(f"ANSWER=====\n{response}\n====")

    status = get_ooc_status(response)
    if not status:
        status = chat.status

    response = strip_ooc_status(response)

    return ChatOut(text=response, status=status)
