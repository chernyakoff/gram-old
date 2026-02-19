from datetime import datetime, timedelta, timezone
from html import escape
from io import StringIO

import httpx
from jose import jwt

from models.orm import Account, Dialog, Recipient
from config import config


def get_api_url(endpoint: str) -> str:
    return f"https://api.telegram.org/bot{config.api.bot.token.get_secret_value()}/{endpoint}"


def create_dialog_share_token(
    *, dialog_id: int, user_id: int, ttl_hours: int = 72
) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    payload = {
        "sub": str(user_id),
        "dialog_id": dialog_id,
        "scope": "dialog_share",
        "exp": exp,
    }
    return jwt.encode(
        payload, config.api.jwt.secret, algorithm=config.api.jwt.algorithm
    )


async def build_dialog_text_file(dialog_id: int) -> tuple[str, str, bytes]:
    """
    Возвращает (filename, file_bytes).
    """
    dialog = (
        await Dialog.get(id=dialog_id)
        .select_related("recipient", "account")
        .prefetch_related("messages")
    )

    recipient = dialog.recipient
    account = dialog.account

    # Заголовок файла
    buf = StringIO()
    buf.write(f"Диалог #{dialog.id}\n")
    buf.write(f"Аккаунт: {account.display_username}\n")
    buf.write(f"Получатель: {recipient.username}\n")
    buf.write(f"Начат: {dialog.started_at}\n")
    buf.write(f"Завершён: {dialog.finished_at}\n")
    buf.write("\n=====================\n\n")

    # Сообщения
    msgs = sorted(dialog.messages, key=lambda m: m.created_at)

    for msg in msgs:
        author = (
            account.display_username
            if msg.sender.name == "ACCOUNT"
            else recipient.username
        )

        time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")

        buf.write(f"[{time}] {author}:\n")
        buf.write(f"{msg.text or ''}\n\n")

    filename = f"dialog_{dialog.id}.txt"
    file_bytes = buf.getvalue().encode("utf-8")

    caption = f"Новая заявка от @{recipient.username}"

    return caption, filename, file_bytes


async def notify_complete_dialog(dialog: Dialog, account: Account) -> None:
    token = create_dialog_share_token(dialog_id=dialog.id, user_id=account.user_id)
    base_url = (config.api.url or "").rstrip("/")
    if not base_url:
        # Fallback для окружений без api.url в конфиге
        base_url = f"{config.web.url.rstrip('/')}/api"
    dialog_url = f"{base_url}/dialogs/shared/{token}"
    recipient = await Recipient.get_or_none(id=dialog.recipient_id)
    username = escape((recipient.username if recipient else None) or "unknown")
    text = (
        f"Новая заявка от @{username}\n"
        "Актуальный диалог по ссылке:\n"
        f"{dialog_url}"
    )
    await send_text_to_user(chat_id=account.user_id, text=text)


async def notify_mailing_end(user_id: int, mailing_name: str, project_name: str) -> None:
    text = f"Рассылка '{mailing_name}' проекта '{project_name}' завершена"
    await send_text_to_user(chat_id=user_id, text=text)


async def send_file_to_user(chat_id: int, filename: str, content: bytes, caption: str):
    files = {
        "document": (filename, content, "text/plain"),
    }
    data = {
        "chat_id": str(chat_id),
        "caption": caption,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            get_api_url("sendDocument"), data=data, files=files
        )
        response.raise_for_status()
        return response.json()


async def send_text_to_user(chat_id: int, text: str):
    data = {
        "chat_id": str(chat_id),
        "text": text,
        "parse_mode": "HTML",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(get_api_url("sendMessage"), data=data)
        response.raise_for_status()
        return response.json()


class BotNotify:
    @classmethod
    async def _send(cls, chat_id: int, msg: str) -> None:
        await send_text_to_user(chat_id, msg)

    @classmethod
    async def error(cls, chat_id: int, msg: str) -> None:
        await cls._send(chat_id, f"⛔ {msg}")

    @classmethod
    async def info(cls, chat_id: int, msg: str) -> None:
        await cls._send(chat_id, f"💡 {msg}")

    @classmethod
    async def success(cls, chat_id: int, msg: str) -> None:
        await cls._send(chat_id, f"✅ {msg}")

    @classmethod
    async def warning(cls, chat_id: int, msg: str) -> None:
        await cls._send(chat_id, f"⚠️ {msg}")
