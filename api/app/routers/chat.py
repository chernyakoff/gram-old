from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from app.common.models import orm
from app.common.models.enums import DialogStatus
from app.common.utils.functions import generate_message
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


def normalize_dashes(text: str) -> str:
    # набор всех популярных видов длинных/средних тире и похожих символов
    long_dashes = {
        "--",
        "—",  # em dash
        "–",  # en dash
        "―",  # horizontal bar
        "−",  # minus sign
        "-",  # non-breaking hyphen (иногда мешает)
    }
    for d in long_dashes:
        text = text.replace(d, "-")
    return text


@router.post("/", response_model=ChatOut)
async def chat(chat: ChatIn, user=Depends(get_current_user)):
    project = await orm.Project.filter(
        id=chat.project_id, user_id=user.id
    ).get_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not chat.messages and project.first_message:
        first_message = generate_message(project.first_message)
        return ChatOut(text=first_message, status=chat.status)
    else:
        for msg in reversed(chat.messages):
            if msg.role == MessageRole.user:
                msg.text = f"{msg.text}\n{get_status_addon(chat.status)}"
                if chat.status == DialogStatus.CLOSING:
                    msg.text += "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"

                break

    orm_prompt = await orm.Prompt.get(project_id=project.id)
    prompt = await build_prompt(orm_prompt.to_dict(), chat.status)

    messages = [{"role": "system", "content": prompt}]
    messages.extend([{"role": m.role.value, "content": m.text} for m in chat.messages])

    completion = await client.chat.completions.create(
        model=config.openai.model,
        messages=messages,  # type: ignore
    )

    response = completion.choices[0].message.content or ""

    status = get_ooc_status(response)
    if not status:
        status = chat.status

    response = strip_ooc_status(response)
    response = normalize_dashes(response)
    return ChatOut(text=response, status=status)
