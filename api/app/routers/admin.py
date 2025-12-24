from decimal import ROUND_DOWN, Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from tortoise import Tortoise

from app.common.models import orm
from app.common.utils import openrouter
from app.config import config
from app.routers.auth import (
    admin_required,
    create_impersonation_tokens,
    get_current_user,
)

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
    data: ImpersonateIn, response: Response, admin=Depends(get_current_user)
):
    username = data.username.removeprefix("https://t.me/").removeprefix("@")
    user = await orm.User.get_or_none(username=username)

    if not user:
        raise HTTPException(status_code=404, detail="Project not found")

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
async def stop_impersonate(response: Response):
    response.delete_cookie("refresh_token", path="/")
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
