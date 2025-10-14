from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models import orm
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
    twofa: str | None
    country: str
    active: bool
    busy: bool
    created_at: datetime
    photos: list[AccountPhotoOut]
    project: ProjectBase | None

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
