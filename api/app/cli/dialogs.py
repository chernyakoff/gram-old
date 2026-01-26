import os
from datetime import datetime
from typing import Any, Dict, List

from cyclopts import App
from rich import print
from tortoise.expressions import Q

from app.common.models import orm
from app.common.models.enums import DialogStatus, MessageSender

app = App(name="dialogs")


def fmt_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.strftime("%d.%m.%Y %H:%M")


def fmt_time(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.strftime("%H:%M")


async def get_user_dialogs_by_username(username: str) -> List[Dict[str, Any]]:
    dialogs = (
        await orm.Dialog.filter(account__user__username=username)
        .select_related(
            "account",
            "account__project",
            "recipient",
        )
        .prefetch_related(
            "messages",
        )
        .order_by("-started_at")
    )

    result: List[Dict[str, Any]] = []

    for dialog in dialogs:
        account = dialog.account
        project = account.project
        recipient = dialog.recipient

        messages = sorted(dialog.messages, key=lambda m: m.tg_message_id or 0)

        result.append(
            {
                "dialog_id": dialog.id,
                "project_id": project.id if project else None,
                "project_name": project.name if project else None,
                "account_username": account.username,
                "recipient_username": recipient.username,
                "dialog_started_at": fmt_dt(dialog.started_at),
                "dialog_finished_at": fmt_dt(dialog.finished_at),
                "dialog_status": dialog.status.value,
                "messages": [
                    {
                        "sender": (
                            account.username
                            if msg.sender == MessageSender.ACCOUNT
                            else recipient.username
                            if msg.sender == MessageSender.RECIPIENT
                            else "system"
                        ),
                        "text": msg.text,
                        "created_at": fmt_time(msg.created_at),
                    }
                    for msg in messages
                ],
            }
        )

    return result


@app.default
async def _():
    data = await get_user_dialogs_by_username("chernyakoff")
    print(data)
