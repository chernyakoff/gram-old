from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models import enums, orm
from app.config import config
from app.dto.project import ProjectBase


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

    twofa: str | None
    country: str
    active: bool
    busy: bool
    created_at: datetime
    photos: list[AccountPhotoOut]
    project: ProjectBase | None
    status: enums.AccountStatus
    muted_until: Optional[datetime]
    out_daily_limit: int
    is_dynamic_limit: bool
    dynamic_daily_limit: int | None
    premiumed_at: Optional[datetime] = None

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


class AccountsCheckIn(BaseModel):
    account_ids: list[int]
