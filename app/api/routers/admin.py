import json
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from tortoise import Tortoise

from api.routers.auth import admin_required
from models import orm
from models.orm import DialogStatus, MessageSender
from utils import openrouter

router = APIRouter(prefix="/admin", tags=["admin"])


class AppSettingIn(BaseModel):
    path: str
    value: str


@router.get(
    "/app-setting/{path}",
    dependencies=[Depends(admin_required)],
)
async def get_settings(path: str) -> str:
    if "." not in path:
        raise HTTPException(status_code=404, detail="Invalid path")

    return await orm.AppSettings.fetch(path)


@router.post(
    "/app-setting",
    dependencies=[Depends(admin_required)],
)
async def upsert_setting(data: AppSettingIn):
    if "." not in data.path:
        raise HTTPException(status_code=404, detail="Invalid path")

    await orm.AppSettings.upsert(data.path, data.value)


class GetBalanceOut(BaseModel):
    openrouter: float
    users: float


async def get_users_balance():
    rows = await Tortoise.get_connection("default").execute_query_dict(
        "SELECT SUM(balance) as total FROM users"
    )
    return (Decimal(rows[0]["total"]) / Decimal(100)).quantize(
        Decimal("0.00"), rounding=ROUND_DOWN
    )


@router.get(
    "/balance", response_model=GetBalanceOut, dependencies=[Depends(admin_required)]
)
async def get_balance():
    or_balance = await openrouter.get_balance()
    users_balance = await get_users_balance()
    return GetBalanceOut(openrouter=float(or_balance), users=float(users_balance))


def fmt_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.strftime("%d.%m.%Y %H:%M")


def fmt_time(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.strftime("%H:%M")


async def get_user_dialogs_by_username(
    username: str, status: Optional[DialogStatus] = None
) -> list[dict[str, Any]]:
    qs = (
        orm.Dialog.filter(account__user__username=username)
        .select_related(
            "account",
            "account__project",
            "recipient",
        )
        .prefetch_related("messages")
        .order_by("-started_at")
    )

    if status is not None:
        qs = qs.filter(status=status)

    dialogs = await qs

    result: list[dict[str, Any]] = []

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


class DialogsDownloadIn(BaseModel):
    username: str
    status: Optional[DialogStatus] = None


@router.post("/dialogs", dependencies=[Depends(admin_required)])
async def get_dialogs(data: DialogsDownloadIn):
    dialogs = await get_user_dialogs_by_username(data.username, data.status)

    content = json.dumps(dialogs, ensure_ascii=False, indent=2)

    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="dialogs_{data.username}.json"',
            "Content-Length": str(len(content.encode("utf-8"))),  # Важно!
        },
    )
