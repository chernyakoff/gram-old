import httpx
from tortoise.expressions import Q

from app.config import config


async def notify_mailing_end(user_id: int, mailing_name: str, project_name: str):
    text = f"Рассылка '{mailing_name}' проекта '{project_name}' завершена"
    await send_text_to_user(chat_id=user_id, text=text)


async def send_text_to_user(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{config.api.bot.token}/sendMessage"

    data = {
        "chat_id": str(chat_id),
        "text": text,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        return response.json()


async def send_file_to_user(chat_id: int, filename: str, content: bytes, caption: str):
    url = f"https://api.telegram.org/bot{config.api.bot.token}/sendDocument"

    files = {
        "document": (filename, content, "text/plain"),
    }

    data = {
        "chat_id": str(chat_id),
        "caption": caption,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data, files=files)
        response.raise_for_status()
        return response.json()
