import json
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from tortoise import Tortoise

from api.routers.auth import (
    admin_required,
    create_impersonation_tokens,
    get_real_user,
    set_refresh_cookie,
)
from config import config
from models import orm
from models.orm import DialogStatus, MessageSender
from utils import openrouter

router = APIRouter(prefix="/admin", tags=["admin"])


class LicenseIn(BaseModel):
    username: str
    days: int


class LicenseOut(BaseModel):
    status: Literal["success", "error"]
    message: str


class ImpersonateIn(BaseModel):
    username: str


class ImpersonateOut(BaseModel):
    access: str


@router.post(
    "/license", response_model=LicenseOut, dependencies=[Depends(admin_required)]
)
async def extend_license(data: LicenseIn):
    username = data.username.removeprefix("https://t.me/").removeprefix("@")
    user = await orm.User.get_or_none(username=username)
    if not user:
        return LicenseOut(status="error", message="Пользователь не найден")

    await user.extend_license(data.days)

    display_date = user.license_end_date.strftime("%d.%m.%Y")

    return LicenseOut(status="success", message=f"Выписана лицензия до {display_date}")


@router.post(
    "/impersonate",
    response_model=ImpersonateOut,
    dependencies=[Depends(admin_required)],
)
async def impersonate(
    data: ImpersonateIn, response: Response, admin=Depends(get_real_user)
):
    username = data.username.removeprefix("https://t.me/").removeprefix("@")
    user = await orm.User.get_or_none(username=username)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot impersonate yourself")

    access, refresh = create_impersonation_tokens(user.id, admin.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite="none" if config.web.url.startswith("https") else "lax",
        secure=config.web.url.startswith("https"),
        max_age=config.api.jwt.refresh_expire_days * 24 * 60 * 60,
        path="/",
    )

    return ImpersonateOut(access=access)


@router.post("/stop-impersonate")
async def stop_impersonate(response: Response, admin=Depends(admin_required)):
    # Restore admin refresh cookie (if any impersonation was active). This keeps the admin logged in
    # without forcing a full re-login.
    set_refresh_cookie(response, admin.id)
    return {"status": "ok"}


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


class BalanceIn(BaseModel):
    username: str
    amount: int


class BalanceOut(BaseModel):
    status: Literal["success", "error"]
    message: str


@router.post(
    "/balance", response_model=BalanceOut, dependencies=[Depends(admin_required)]
)
async def add_balance(data: BalanceIn):
    username = data.username.removeprefix("https://t.me/").removeprefix("@")
    user = await orm.User.get_or_none(username=username)
    if not user:
        return BalanceOut(status="error", message="Пользователь не найден")

    await user.add_balance(data.amount)

    return BalanceOut(status="success", message=f"Баланс пополнен на {data.amount} руб")


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
