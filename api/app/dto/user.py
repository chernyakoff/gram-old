from pydantic import BaseModel
from tortoise import timezone as tz
from tortoise_serializer import ContextType, Serializer

from app.common.models import orm


class UserLoginIn(BaseModel):
    id: int
    auth_date: int
    hash: str
    first_name: str | None
    last_name: str | None
    username: str | None
    photo_url: str | None
    ref_code: str | None = None


class UserLoginOut(BaseModel):
    access_token: str


class UserOut(Serializer):
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    photo_url: str | None
    role: str
    balance: int
    has_license: bool
    ref_code: str

    @classmethod
    async def resolve_role(cls, instance: orm.User, context: ContextType):
        return instance.role.name

    @classmethod
    async def resolve_has_license(
        cls, instance: orm.User, context: ContextType
    ) -> bool:
        return bool(instance.license_end_date and instance.license_end_date > tz.now())


class UserMeOut(UserOut):
    impersonated: bool | None = None
    real_user_id: int | None = None
