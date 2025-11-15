from io import StringIO

import httpx
from tortoise.expressions import Q

from app.common.models.orm import Account, Dialog
from app.config import config


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

    caption = f"Новаяя завяка от @{recipient.username}"

    return caption, filename, file_bytes


async def send_file_to_user(chat_id: int, filename: str, content: bytes, caption: str):
    url = f"https://api.telegram.org/bot{config.api.bot.token}/sendDocument"

    async with httpx.AsyncClient() as client:
        files = {
            "chat_id": (None, str(chat_id)),
            "document": (filename, content, "text/plain"),
            "caption": caption,
        }
        await client.post(url, files=files)


async def notify_complete_dialog(dialog: Dialog, account: Account):
    caption, filename, content = await build_dialog_text_file(dialog.id)
    await send_file_to_user(account.user_id, filename, content, caption)
