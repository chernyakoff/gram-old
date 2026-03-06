from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from tortoise_serializer import Serializer


class ProxiesBulkCreateIn(BaseModel):
    proxies: list[str]


class EmbedAccountOut(Serializer):
    id: int
    phone: str
    username: str | None


class ProxyOut(Serializer):
    id: int
    host: str
    port: int
    username: str
    password: str
    country: str
    created_at: datetime
    active: bool
    failures: int
    account: Optional[EmbedAccountOut] = None


class ProxiesCountryIn(BaseModel):
    country: str
    ids: list[int]
