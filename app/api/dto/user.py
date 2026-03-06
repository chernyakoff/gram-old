from pydantic import BaseModel
from tortoise_serializer import Serializer

class UserLoginIn(BaseModel):
    id: int
    auth_date: int
    hash: str
    first_name: str | None
    last_name: str | None
    username: str | None
    photo_url: str | None
    invite_ref_code: str | None = None


class UserLoginOut(BaseModel):
    access_token: str


class UserOut(Serializer):
    id: int


class UserMeOut(UserOut):
    impersonated: bool | None = None
    real_user_id: int | None = None
