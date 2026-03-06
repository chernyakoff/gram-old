from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from models import orm
from config import config
from api.dto.project import ProjectBase


class AccountsBulkCreateIn(BaseModel):
    s3path: str


class AccountPhotoOut(Serializer):
    id: int
    url: str


class AccountPhotosIn(BaseModel):
    delete: list[int]
    upload: list[str]


class AccountBase(Serializer):
    username: str | None
    about: str | None
    channel: str | None
    first_name: str | None
    last_name: str | None


class AccountIn(AccountBase):
    photos: AccountPhotosIn


class AccountOut(AccountBase):
    id: int
    phone: str
    premium: bool
    premium_stopped: bool
    proxy: str | None

    twofa: str | None
    country: str
    active: bool
    busy: bool
    created_at: datetime
    photos: list[AccountPhotoOut]
    project: ProjectBase | None
    status: orm.AccountStatus
    muted_until: Optional[datetime]
    out_daily_limit: int
    is_dynamic_limit: bool
    dynamic_daily_limit: int | None
    premiumed_at: Optional[datetime] = None
    dialogs_count: int

    @classmethod
    async def resolve_proxy(cls, instance: orm.Account, context: ContextType) -> str | None:
        proxy = getattr(instance, "proxy", None)
        if not proxy:
            return None
        return f"{proxy.host}:{proxy.port}"

    @classmethod
    async def resolve_is_dynamic_limit(cls, instance, context):
        return instance.active_days_count < len(instance.PROGREV)

    @classmethod
    async def resolve_dynamic_daily_limit(cls, instance, context):
        if instance.active_days_count >= len(instance.PROGREV):
            return None
        if not instance.premium:
            return 1
        return instance.PROGREV[instance.active_days_count]

    @classmethod
    async def resolve_photos(
        cls, instance: orm.Account, context: ContextType
    ) -> list[AccountPhotoOut]:
        return [
            AccountPhotoOut(url=f"{config.s3.public_endpoint_url}/{p.path}", id=p.id)
            for p in instance.photos  # type: ignore
        ]

    @classmethod
    async def resolve_is_dynamic_limit(
        cls, instance: orm.Account, context: ContextType
    ) -> bool:
        active_days_map = context.get("active_days_map", {})
        active_days = active_days_map.get(instance.id, 0)
        return active_days < len(instance.PROGREV)

    @classmethod
    async def resolve_dynamic_daily_limit(
        cls, instance: orm.Account, context: ContextType
    ) -> int | None:
        active_days_map = context.get("active_days_map", {})
        active_days = active_days_map.get(instance.id, 0)

        if active_days >= len(instance.PROGREV):
            return None

        return instance.PROGREV[active_days]


class BindProjectIn(BaseModel):
    project_id: int
    account_ids: list[int]


class SetLimitIn(BaseModel):
    out_daily_limit: int
    account_ids: list[int]


class AccountListOut(Serializer):
    id: int
    name: str
    phone: str

    @classmethod
    async def resolve_name(cls, instance: orm.Account, context: ContextType):
        return instance.display_username


class AccountStateOut(Serializer):
    id: int
    busy: bool
    status: orm.AccountStatus
    premium: bool


class PremiumConfirmIn(BaseModel):
    purchased: bool


class PremiumConfirmOut(BaseModel):
    status: str
    message: str | None = None
    stop_workflow_id: str | None = None


class AccountsCheckIn(BaseModel):
    account_ids: list[int]
