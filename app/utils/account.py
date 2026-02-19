import json
import random
from dataclasses import asdict, dataclass
from typing import Any, Optional, Self

import phonenumbers  # type: ignore
from aiopath import AsyncPath
from telethon import TelegramClient  # type: ignore
from telethon.sessions import MemorySession, StringSession  # type: ignore

from models import orm


@dataclass
class AccountFile:
    session: AsyncPath
    json: AsyncPath


@dataclass
class AccountIn:
    id: int
    user_id: int
    proxy_id: int
    session: str
    premium: bool
    username: str | None
    first_name: str | None
    last_name: str | None
    channel: str | None
    about: str | None


CFG = {
    "id": 2040,
    "app_hash": "b18441a1ff607e10a989891a5462e627",
    "key_map": {
        "app_id": ["app_id", "api_id"],
        "app_hash": ["app_hash", "api_hash"],
        "twofa": [
            "twoFA",
            "password",
            "twostep",
            "password2FA",
            "twofa",
            "password2fa",
        ],
        "device_model": ["device"],
        "system_version": ["sdk"],
        "app_version": ["app_version"],
    },
    # Profiles are aligned with existing imported JSONs (Windows + x64 app versions).
    "profile": {
        "system_versions": ["Windows 8", "Windows 8.1", "Windows 10", "Windows 11"],
        "app_versions": [
            "5.3.1 x64",
            "5.3.2 x64",
            "5.5.5 x64",
            "5.5.8 x64",
            "5.6.2 x64",
            "5.9.0 x64",
            "5.10.2 x64",
        ],
        "device_models": [
            "MYD82",
            "4313CTO",
            "B150I GAMING PRO AC",
            "M5A99X EVO skt940",
            "M5A88-M VGA mATX skt940",
            "785GM-S3 VGA mATX skt940",
            "H252-3C0 (rev. 100)",
            "970A-G43 PLUS (MS-7974)",
            "B75M-D3H",
            "P8H61-M LX3 R2.0",
        ],
    },
}


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
    memory_session: bool = False

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
        if self.memory_session:
            params["session"] = MemorySession()
        return TelegramClient(**params)

    def to_orm(self, account: AccountIn) -> orm.Account:
        params = {
            "app_id": self.app_id,
            "app_hash": self.app_hash,
            "twofa": self.twofa,
            "country": self.country,
            "device_model": self.device_model,
            "system_version": self.system_version,
            "app_version": self.app_version,
            "phone": self.phone,
            "id": account.id,
            "first_name": account.first_name,
            "last_name": account.last_name,
            "username": account.username,
            "premium": account.premium,
            "user_id": account.user_id,
            "session": account.session,
            "about": account.about,
            "channel": account.channel,
        }
        return orm.Account(**params)

    @staticmethod
    def infer_country_from_phone(phone: str | None) -> str:
        if phone:
            normalized = "".join(ch for ch in phone if ch.isdigit())
            if normalized:
                try:
                    parsed = phonenumbers.parse(f"+{normalized}")
                    code = phonenumbers.region_code_for_number(parsed)
                    if code:
                        return code
                except Exception:
                    pass
        return "US"

    @classmethod
    def random_client_profile(cls) -> dict[str, str]:
        return {
            "device_model": random.choice(CFG["profile"]["device_models"]),
            "system_version": random.choice(CFG["profile"]["system_versions"]),
            "app_version": random.choice(CFG["profile"]["app_versions"]),
        }

    @classmethod
    def from_telethon_string(
        cls,
        session_string: str,
        phone: str | None = None,
        twofa: str | None = None,
        country: str | None = None,
    ) -> Self:
        profile = cls.random_client_profile()
        normalized_phone = "".join(ch for ch in (phone or "") if ch.isdigit())
        resolved_country = country or cls.infer_country_from_phone(normalized_phone)
        return cls(
            app_id=CFG["id"],
            app_hash=CFG["app_hash"],
            device_model=profile["device_model"],
            system_version=profile["system_version"],
            app_version=profile["app_version"],
            twofa=twofa or "",
            country=resolved_country,
            phone=normalized_phone or "00000000000",
            session_string=session_string,
        )

    @classmethod
    def from_orm(cls, orm_account: orm.Account) -> Self:
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

    @classmethod
    async def instance(cls, file: AccountFile) -> Self:
        result: dict[str, Any] = dict()
        result["session_file"] = file.session
        result["phone"] = file.session.stem
        if not result["phone"].isdigit():
            raise ValueError("Имя файла не является номером телефона")

        result["country"] = cls.infer_country_from_phone(result["phone"])
        fallback_profile = cls.random_client_profile()

        content = await file.json.read_text()
        data = json.loads(content)

        for field, keys in CFG["key_map"].items():
            value = None
            for k in keys:
                if k in data and data[k]:
                    value = data[k]
                    break
            if not value:
                if field == "device_model":
                    value = fallback_profile["device_model"]
                elif field == "system_version":
                    value = fallback_profile["system_version"]
                elif field == "app_version":
                    value = fallback_profile["app_version"]
                elif field == "app_id":
                    value = CFG["id"]
                elif field == "app_hash":
                    value = CFG["app_hash"]
                elif field == "twofa":
                    value = ""

            if field == "app_id":
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = CFG["id"]
            elif field == "app_hash":
                value = str(value)
            elif field in {"device_model", "system_version", "app_version", "twofa"}:
                value = str(value)

            result[field] = value

        return cls(**result)

    def model_dump(self):
        return asdict(self)
