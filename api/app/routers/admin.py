from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.common.models import orm
from app.routers.auth import admin_required

router = APIRouter(prefix="/admin", tags=["admin"])


class LicenseIn(BaseModel):
    username: str
    days: int


class LicenseOut(BaseModel):
    status: Literal["success", "error"]
    message: str


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
