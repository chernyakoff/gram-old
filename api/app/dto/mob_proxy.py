from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import Serializer


class MobProxyCreateIn(BaseModel):
    host: str
    port: int
    username: str
    password: str
    change_url: str
    country: str
    active: bool = True


class MobProxyUpdateIn(BaseModel):
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    change_url: str | None = None
    country: str | None = None
    active: bool | None = None


class MobProxyOut(Serializer):
    id: int
    host: str
    port: int
    username: str
    password: str
    change_url: str
    country: str
    active: bool
    failures: int
    created_at: datetime
