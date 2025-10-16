import re
from dataclasses import dataclass
from typing import Optional, Self
from urllib.parse import urlparse

import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType

from app.common.models.orm import Proxy as OrmProxy
from app.config import config

IPV4_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

timeout = aiohttp.ClientTimeout(total=20)


@dataclass
class Proxy:
    host: str
    port: int
    username: str
    password: str
    type: ProxyType = ProxyType.SOCKS5
    scheme: str = "socks5"

    @classmethod
    def from_line(cls, line: str) -> Self:
        parts = list(map(str.strip, line.strip().split(":")))
        if len(parts) != 4:
            raise ValueError(f"Неверный формат: {line}")
        host, port_str, username, password = parts
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(
                f"Порт должен быть числом, получено: {port_str!r} в строке: {line}"
            )

        return cls(host=host, port=port, username=username, password=password)

    @classmethod
    def from_dsn(cls, dsn: str) -> Self:
        parsed = urlparse(dsn)
        if not all(
            [
                parsed.scheme,
                parsed.hostname,
                parsed.port,
                parsed.username,
                parsed.password,
            ]
        ):
            raise ValueError(f"Неверный DSN: {dsn}")

        assert parsed.hostname is not None, f"DSN без hostname: {dsn}"
        assert parsed.port is not None, f"DSN без порта: {dsn}"
        assert parsed.username is not None, f"DSN без username: {dsn}"
        assert parsed.password is not None, f"DSN без password: {dsn}"

        if parsed.scheme.lower() != cls.scheme:
            raise ValueError(f"Неверный тип прокси: {parsed.scheme}")

        return cls(
            host=parsed.hostname,
            port=parsed.port,
            username=parsed.username,
            password=parsed.password,
        )

    @classmethod
    def from_orm(cls, orm_proxy: OrmProxy) -> Self:
        return cls(
            host=orm_proxy.host,
            port=orm_proxy.port,
            username=orm_proxy.username,
            password=orm_proxy.password,
        )

    def to_orm(self, user_id: int, country: str) -> OrmProxy:
        return OrmProxy(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            user_id=user_id,
            country=country,
        )

    def __str__(self):
        return self.line

    @property
    def line(self):
        return (
            f"{self.port}:{self.username}:{self.password}:{self.password}@{self.host}"
        )

    @property
    def dsn(self):
        return (
            f"{self.scheme}://{self.username}:{self.password}@{self.host}:{self.port}"
        )

    @property
    def connector(self):
        return ProxyConnector(
            proxy_type=self.type,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            rdns=True,
        )

    async def check(self) -> Optional[str]:
        try:
            async with aiohttp.ClientSession(
                connector=self.connector, timeout=timeout
            ) as session:
                async with session.get(
                    "https://api.ipify.org/?format=text"
                ) as response:
                    ip = (await response.text()).strip()
                    if IPV4_REGEX.fullmatch(ip):
                        return ip
        except Exception:
            pass  # Можно добавить логгирование

        return None

    async def get_country(self, ip: str) -> Optional[str]:
        url = f"https://ipinfo.io/{ip}"
        params = {"token": config.ipinfo.token}
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()  # поднимает исключение для 4xx/5xx
                    data = await response.json()
                    return data.get("country")  # безопасный доступ
        except Exception:
            return None  # можно логировать при необходимости
