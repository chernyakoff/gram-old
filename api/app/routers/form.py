import asyncio
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.common.models.orm import Role, User
from app.common.utils.notify import send_text_to_user


class CallbackFormIn(BaseModel):
    name: str
    phone: str
    telegram: Optional[str] = None


router = APIRouter(prefix="/form", tags=["form"])

CHANNEL_ID = -1003866275203


async def send_messages(data: CallbackFormIn):

    text = ["Форма обратной связи (тарифы)"]
    text.append("")
    text.append(f"<b>Имя:</b> {data.name}")
    text.append(f"<b>Телефон:</b> {data.phone}")
    if data.telegram:
        data.telegram = data.telegram.removeprefix("https://t.me/").removeprefix("@")
        text.append(f"<b>Телеграм:</b> @{data.telegram}")

    try:
        await send_text_to_user(chat_id=CHANNEL_ID, text="\n".join(text))
        await asyncio.sleep(0.3)
    except:
        pass


@router.post("/callback")
async def save_timezone(data: CallbackFormIn):
    asyncio.create_task(send_messages(data))
    return {"success": "ok"}
