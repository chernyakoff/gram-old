from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import Serializer


class ProxiesBulkCreateIn(BaseModel):
    proxies: list[str]


class ProxyOut(Serializer):
    id: int
    host: str
    port: int
    username: str
    password: str
    country: str
    created_at: datetime


class ProxiesCountryIn(BaseModel):
    country: str
    ids: list[int]
