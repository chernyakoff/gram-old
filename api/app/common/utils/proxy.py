import asyncio
import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Self
from urllib.parse import urlparse

import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType  # type: ignore
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models.orm import Proxy
from app.config import config

IPV4_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

timeout = aiohttp.ClientTimeout(total=5)


@dataclass
class ProxyUtil:
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
    def from_orm(cls, orm_proxy: Proxy) -> Self:
        return cls(
            host=orm_proxy.host,
            port=orm_proxy.port,
            username=orm_proxy.username,
            password=orm_proxy.password,
        )

    def to_orm(self, user_id: int, country: str) -> Proxy:
        return Proxy(
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
        params = {"token": config.ipinfo.token}  # type: ignore
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:  # type: ignore
                async with session.get(url, params=params) as response:
                    response.raise_for_status()  # поднимает исключение для 4xx/5xx
                    data = await response.json()
                    return data.get("country")  # безопасный доступ
        except Exception:
            return None  # можно логировать при необходимости


# --------


async def get_user_proxies(user_id: int) -> list[Proxy]:
    semaphore = asyncio.Semaphore(10)

    async def check_proxy(orm_proxy: Proxy) -> Proxy | None:
        async with semaphore:
            proxy = ProxyUtil.from_orm(orm_proxy)
            if await proxy.check():
                return orm_proxy
        return None

    orm_proxies = await Proxy.filter(user_id=user_id).all()
    results = await asyncio.gather(*(check_proxy(p) for p in orm_proxies))
    return [p for p in results if p is not None]


# -------------------------------------------------------------------------------
FAILURE_THRESHOLD = 5  # после 5 фейлов — прокси отключаем
FAILURE_DECAY = 1  # на сколько уменьшать failures при heartbeat
DECAY_INTERVALS_BEFORE_ZERO = (
    10  # сколько heartbeats нужно, чтобы failures вернулись к 0
)


class ProxyPool:
    def __init__(self, user_id: int, ttl: int = 30, heartbeat_interval: int = 10):
        self.user_id = user_id
        self.ttl = ttl
        self.heartbeat_interval = heartbeat_interval

        # proxy_id -> session_id
        self._active_proxies: dict[int, str] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None

    # --------------------------------------------------------------
    # Контекст
    # --------------------------------------------------------------
    @asynccontextmanager
    async def proxy(
        self, country: str, timeout: int = 30, account_id: int | None = None
    ) -> AsyncIterator[Proxy]:
        start = asyncio.get_event_loop().time()
        delay = 1
        proxy = None

        while True:
            proxy = await self.acquire(country, account_id)
            if proxy:
                break
            if asyncio.get_event_loop().time() - start > timeout:
                raise TimeoutError(
                    f"No proxy available for country {country} after {timeout}s"
                )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 5)

        try:
            yield proxy
        finally:
            await self.release(proxy)

    # --------------------------------------------------------------
    # Release
    # --------------------------------------------------------------
    async def release(self, proxy: Proxy):
        async with self._lock:
            self._active_proxies.pop(proxy.id, None)

        await Proxy.filter(id=proxy.id, lock_session=proxy.lock_session).update(
            locked_until=None, lock_session=None
        )

    # --------------------------------------------------------------
    # Acquire
    # --------------------------------------------------------------
    async def acquire(self, country: str, account_id: int | None) -> Proxy | None:
        session_id = str(uuid.uuid4())

        # запускаем heartbeat если его нет
        async with self._lock:
            if not self._heartbeat_task or self._heartbeat_task.done():
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        while True:
            orm_proxy = await self._try_acquire_proxy(country, session_id, account_id)
            if not orm_proxy:
                return None

            # проверяем прокси на живость
            proxy_model = ProxyUtil.from_orm(orm_proxy)
            if await proxy_model.check():
                await self._on_success(orm_proxy, account_id)
                async with self._lock:
                    self._active_proxies[orm_proxy.id] = session_id
                return orm_proxy

            # прокси упал → наказываем, отвязываем, отключаем
            await self._on_failure(orm_proxy, account_id)
            await self.release(orm_proxy)
            # продолжаем искать следующий прокси

    # --------------------------------------------------------------
    # Private: попытаться взять конкретный прокси
    # --------------------------------------------------------------
    async def _try_acquire_proxy(
        self, country: str, session_id: str, account_id: int | None
    ):
        async with in_transaction("default") as conn:
            # 1. Сначала пытаемся вернуть last_proxy_id
            if account_id:
                rows = await conn.execute_query_dict(
                    "SELECT last_proxy_id FROM accounts WHERE id = $1", [account_id]
                )
                if rows and rows[0]["last_proxy_id"]:
                    pid = rows[0]["last_proxy_id"]

                    rows2 = await conn.execute_query_dict(
                        """
                        UPDATE proxies
                        SET locked_until = NOW() + make_interval(secs => $1),
                            lock_session = $2
                        WHERE id = $3
                          AND country = $4
                          AND user_id = $5
                          AND active = TRUE
                          AND (locked_until IS NULL OR locked_until < NOW())
                        RETURNING *;
                        """,
                        [self.ttl, session_id, pid, country, self.user_id],
                    )
                    if rows2:
                        p = Proxy(**rows2[0])
                        p._saved_in_db = True
                        return p

            # 2. Иначе берём "лучший" прокси
            rows = await conn.execute_query_dict(
                """
                WITH ranked AS (
                    SELECT p.id
                    FROM proxies p
                    LEFT JOIN accounts a ON a.last_proxy_id = p.id
                    WHERE p.country = $1
                      AND p.user_id = $2
                      AND p.active = TRUE
                      AND (p.locked_until IS NULL OR p.locked_until < NOW())
                    GROUP BY p.id, p.failures
                    ORDER BY p.failures ASC,
                             COUNT(a.id) ASC,
                             RANDOM()
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE proxies
                SET locked_until = NOW() + make_interval(secs => $3),
                    lock_session = $4
                WHERE id IN (SELECT id FROM ranked)
                RETURNING *;
                """,
                [country, self.user_id, self.ttl, session_id],
            )

            if not rows:
                return None

            p = Proxy(**rows[0])
            p._saved_in_db = True
            return p

    # --------------------------------------------------------------
    # Success handler
    # --------------------------------------------------------------
    async def _on_success(self, proxy: Proxy, account_id: int | None):
        """
        Прокси жив → уменьшаем failures до нуля.
        Привязываем его к аккаунту.
        """
        async with in_transaction("default") as conn:
            # если failures > 0 → уменьшаем
            await conn.execute_query(
                """
                UPDATE proxies
                SET failures = GREATEST(failures - 1, 0)
                WHERE id = $1
                """,
                [proxy.id],
            )

            if account_id:
                await conn.execute_query(
                    """
                    UPDATE accounts
                    SET last_proxy_id = $1
                    WHERE id = $2
                    """,
                    [proxy.id, account_id],
                )

    # --------------------------------------------------------------
    # Failure handler
    # --------------------------------------------------------------
    async def _on_failure(self, proxy: Proxy, account_id: int | None):
        async with in_transaction("default") as conn:
            # увеличиваем failures
            await conn.execute_query(
                """
                UPDATE proxies
                SET failures = failures + 1
                WHERE id = $1
                """,
                [proxy.id],
            )

            # сбрасываем привязку аккаунта
            if account_id:
                await conn.execute_query(
                    """
                    UPDATE accounts
                    SET last_proxy_id = NULL
                    WHERE id = $1 AND last_proxy_id = $2
                    """,
                    [account_id, proxy.id],
                )

            # если прокси стал совсем плохим → отключаем
            await conn.execute_query(
                """
                UPDATE proxies
                SET active = FALSE
                WHERE id = $1 AND failures >= $2
                """,
                [proxy.id, FAILURE_THRESHOLD],
            )

    # --------------------------------------------------------------
    # Heartbeat
    # --------------------------------------------------------------
    async def _heartbeat_loop(self):
        """
        Делает две вещи:
        - продлевает lock
        - делает decay failures
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                async with self._lock:
                    if not self._active_proxies:
                        break
                    proxy_ids = list(self._active_proxies.keys())

                async with in_transaction("default") as conn:
                    # 1) продление lock
                    await conn.execute_query(
                        """
                        UPDATE proxies
                        SET locked_until = NOW() + make_interval(secs => $1)
                        WHERE id = ANY($2::int[])
                        """,
                        [self.ttl, proxy_ids],
                    )

                    # 2) decay failures — прокси со временем восстанавливаются
                    await conn.execute_query(
                        """
                        UPDATE proxies
                        SET failures = GREATEST(failures - $1, 0)
                        WHERE id = ANY($2::int[])
                        """,
                        [FAILURE_DECAY, proxy_ids],
                    )

        except asyncio.CancelledError:
            pass
