from dataclasses import dataclass
from typing import Optional, Self

from aiopath import AsyncPath
from telethon import TelegramClient
from telethon.sessions import StringSession

from app.common.models import orm


@dataclass
class AccountUtil:
    app_id: int
    app_hash: str
    device_model: str
    system_version: str
    app_version: str
    twofa: str
    country: str
    phone: str
    session_file: Optional[AsyncPath] = None
    session_string: Optional[str] = None

    def __post_init__(self):
        if not (self.session_file or self.session_string):
            raise ValueError("Нужно указать session_file или session_string")
        if self.session_file and self.session_string:
            raise ValueError(
                "Нельзя указывать одновременно session_file и session_string"
            )

    def create_client(self, proxy: orm.Proxy) -> TelegramClient:
        params = {
            "api_hash": self.app_hash,
            "api_id": self.app_id,
            "device_model": self.device_model,
            "app_version": self.app_version,
            "system_version": self.system_version,
            "session": StringSession(self.session_string)
            if self.session_string
            else str(self.session_file),
            "proxy": {
                "proxy_type": 2,  # socks5
                "addr": proxy.host,
                "port": proxy.port,
                "username": proxy.username,
                "password": proxy.password,
                "rdns": True,
            },
        }
        return TelegramClient(**params)

    @classmethod
    async def from_orm(cls, orm_account: orm.Account) -> Self:
        params = {
            "app_id": orm_account.app_id,
            "app_hash": orm_account.app_hash,
            "twofa": orm_account.twofa,
            "country": orm_account.country,
            "device_model": orm_account.device_model,
            "system_version": orm_account.system_version,
            "app_version": orm_account.app_version,
            "phone": orm_account.phone,
            "session_string": orm_account.session,
        }
        return cls(**params)
