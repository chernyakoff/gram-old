import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncIterator

from tortoise import Tortoise
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models.orm import Proxy


class ProxyPool:
    def __init__(self, user_id: int, ttl: int = 30, heartbeat_interval: int = 10):
        self.user_id = user_id
        self.ttl = ttl
        self.heartbeat_interval = heartbeat_interval

        # proxy_id -> session_id
        self._active_proxies: dict[int, str] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None

    # -------------------- Контекстный менеджер --------------------
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
            if proxy:
                await self.release(proxy)

    # -------------------- Acquire --------------------
    async def acquire(
        self, country: str, account_id: int | None = None
    ) -> Proxy | None:
        session_id = str(uuid.uuid4())
        async with in_transaction("default"):
            conn = Tortoise.get_connection("default")

            # НОВАЯ ЛОГИКА: Если передан account_id, пытаемся взять тот же прокси
            if account_id:
                # Получаем last_proxy_id из аккаунта
                account_data = await conn.execute_query_dict(
                    "SELECT last_proxy_id FROM accounts WHERE id = $1", [account_id]
                )

                if account_data and account_data[0]["last_proxy_id"]:
                    last_proxy_id = account_data[0]["last_proxy_id"]

                    # Пытаемся захватить тот же прокси
                    rows = await conn.execute_query_dict(
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
                        [self.ttl, session_id, last_proxy_id, country, self.user_id],
                    )

                    if rows:
                        proxy = Proxy(**rows[0])
                        proxy._saved_in_db = True

                        async with self._lock:
                            self._active_proxies[proxy.id] = session_id
                            if not self._heartbeat_task or self._heartbeat_task.done():
                                self._heartbeat_task = asyncio.create_task(
                                    self._heartbeat_loop()
                                )

                        return proxy

            # Если не нашли "свой" прокси - берём любой
            rows = await conn.execute_query_dict(
                """
                WITH picked AS (
                    SELECT id
                    FROM proxies
                    WHERE country = $1
                    AND user_id = $2
                    AND active = TRUE
                    AND (locked_until IS NULL OR locked_until < NOW())
                    ORDER BY RANDOM()
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE proxies
                SET locked_until = NOW() + make_interval(secs => $3),
                    lock_session = $4
                WHERE id IN (SELECT id FROM picked)
                RETURNING *;
                """,
                [country, self.user_id, self.ttl, session_id],
            )

            if not rows:
                return None

            proxy = Proxy(**rows[0])
            proxy._saved_in_db = True

            # Сохраняем proxy_id в аккаунте если передан account_id
            if account_id:
                await conn.execute_query(
                    "UPDATE accounts SET last_proxy_id = $1 WHERE id = $2",
                    [proxy.id, account_id],
                )

            async with self._lock:
                self._active_proxies[proxy.id] = session_id
                if not self._heartbeat_task or self._heartbeat_task.done():
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            return proxy

    # -------------------- Release --------------------
    async def release(self, proxy: Proxy):
        async with self._lock:
            self._active_proxies.pop(proxy.id, None)
        await Proxy.filter(id=proxy.id, lock_session=proxy.lock_session).update(
            locked_until=None, lock_session=None
        )

    # -------------------- Центральный Heartbeat --------------------
    async def _heartbeat_loop(self):
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                async with self._lock:
                    if not self._active_proxies:
                        break  # все прокси освобождены → можно завершить heartbeat
                    proxy_ids = list(self._active_proxies.keys())
                    if proxy_ids:
                        await Proxy.filter(id__in=proxy_ids).update(
                            locked_until=tz.now() + timedelta(seconds=self.ttl)
                        )
        except asyncio.CancelledError:
            pass
