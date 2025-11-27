import json
import os

from cyclopts import App
from rich import print
from tortoise.expressions import Q

from app.common.models.enums import DialogStatus, MessageSender
from app.common.models.orm import Account, AppSettings, Dialog, Message, Project

app = App(name="dialogs")


async def save_account_dialogs_to_files(
    usernames: list[str], folder: str = "app/dialogs"
):
    """
    Сохраняет каждый диалог аккаунта с COMPLETE или CLOSING статусом в отдельный файл.
    Файлы называются {account.display_username}-{recipient_name}.txt
    """
    if not usernames:
        print("Список аккаунтов пуст")
        return

    # Создаём папку, если не существует
    os.makedirs(folder, exist_ok=True)

    # Получаем аккаунты с предзагрузкой диалогов и сообщений
    accounts = await Account.filter(username__in=usernames).prefetch_related(
        "dialogs__messages", "dialogs__recipient"
    )

    if not accounts:
        print("Аккаунты не найдены")
        return

    for account in accounts:
        dialogs = [
            d
            for d in account.dialogs
            if d.status in (DialogStatus.COMPLETE, DialogStatus.CLOSING)
        ]

        if not dialogs:
            print(
                f"Нет диалогов со статусом COMPLETE или CLOSING для {account.display_username}"
            )
            continue

        for dialog in dialogs:
            recipient_name = getattr(
                dialog.recipient, "username", f"ID_{dialog.recipient.id}"
            )
            # Формируем корректное имя файла
            safe_account_name = account.display_username.replace("@", "").replace(
                " ", "_"
            )
            safe_recipient_name = str(recipient_name).replace("@", "").replace(" ", "_")
            filename = os.path.join(
                folder, f"{safe_account_name}-{safe_recipient_name}.txt"
            )

            lines = [
                f"Диалог аккаунта {account.display_username} ({account.name}) с {recipient_name}",
                f"Статус: {dialog.status}",
                f"Начат: {dialog.started_at}",
                "-" * 50,
            ]

            messages = sorted(dialog.messages, key=lambda m: m.created_at)
            for msg in messages:
                sender = (
                    "Вы" if msg.sender == MessageSender.ACCOUNT else msg.sender.value
                )
                lines.append(f"[{msg.created_at}] {sender}: {msg.text}")

            lines.append("-" * 50)

            # Записываем в файл
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            print(f"Сохранено: {filename}")


USERNAMES = """
GeLidusF
DavGenMax
TrafficBoostPro
LidsMacsim
DerLibsMaks
SyperMaximus
LeadsAndTrafficX
TrafficLeadForge
TrafMsimz
"""


@app.default
async def _():
    usernames = [u.strip() for u in USERNAMES.strip().splitlines()]
    await save_account_dialogs_to_files(usernames)
