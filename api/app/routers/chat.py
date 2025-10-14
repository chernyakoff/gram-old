from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from app.common.models import orm
from app.common.utils.functions import generate_message
from app.config import config
from app.dto.chat import ChatIn, ChatOut
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
        return ChatOut(text=first_message)

    # иначе строим контекст для модели
    messages = [{"role": "system", "content": project.prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    completion = await client.chat.completions.create(
        model=config.openai.model,
        messages=messages,  # type: ignore
    )
    return ChatOut(text=completion.choices[0].message.content or "")
