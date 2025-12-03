import uuid
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Optional

from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models.orm import Account, AccountStatus, Proxy
from app.common.utils.proxy import ProxyUtil


class Status(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class ProxyLogEntry:
    status: Status
    message: str
    payload: Optional[dict] = None


class ProxyPool:
    MAX_RETRIES = 5
    MAX_FAILURES = 5
    LOCK_TIMEOUT = 30  # секунд

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.logs: list[ProxyLogEntry] = []

    # ----------------- Логи -----------------
    def _add_log(self, status: Status, message: str, payload: Optional[dict] = None):
        self.logs.append(ProxyLogEntry(status=status, message=message, payload=payload))

    def get_logs(self, clear: bool = False) -> list[ProxyLogEntry]:
        logs_copy = self.logs.copy()
        if clear:
            self.logs.clear()
        return logs_copy

    async def _get_free_proxy(self, country: str) -> Optional[Proxy]:
        now = tz.now()
        async with in_transaction() as conn:
            row = await conn.execute_query_dict(
                """
                SELECT p.*
                FROM proxies p
                WHERE p.user_id = $1
                AND p.active = TRUE
                AND p.country = $2
                AND (p.locked_until IS NULL OR p.locked_until < $3)
                AND p.id NOT IN (
                    SELECT proxy_id FROM accounts WHERE proxy_id IS NOT NULL
                )
                ORDER BY p.failures ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """,
                [self.user_id, country, now],
            )
            if not row:
                return None
            proxy = Proxy(**row[0])
            proxy._saved_in_db = True
            proxy.locked_until = now + timedelta(seconds=self.LOCK_TIMEOUT)
            proxy.lock_session = str(uuid.uuid4())
            await proxy.save(
                update_fields=["locked_until", "lock_session"], using_db=conn
            )
            return proxy

    async def _check_proxy(self, proxy: Proxy) -> bool:
        proxy_util = ProxyUtil.from_orm(proxy)
        ok = await proxy_util.check()
        if not ok:
            await self._handle_proxy_failure(proxy)
            return False
        return True

    async def _handle_proxy_failure(self, proxy: Proxy):
        old_failures = proxy.failures
        proxy.failures += 1
        if proxy.failures >= self.MAX_FAILURES:
            proxy.active = False
            self._add_log(
                Status.ERROR,
                "Proxy deactivated due to failures",
                {"proxy_id": proxy.id, "failures": proxy.failures},
            )
        await proxy.save(update_fields=["failures", "active"])
        self._add_log(
            Status.WARNING,
            "Proxy failed check",
            {
                "proxy_id": proxy.id,
                "old_failures": old_failures,
                "failures": proxy.failures,
            },
        )

    async def _deactivate_account(self, account: Account):
        account.active = False
        account.status = AccountStatus.NOPROXY
        await account.save(update_fields=["active", "status"])
        self._add_log(
            Status.WARNING,
            "Account deactivated: proxy is inactive",
            {"account_id": account.id, "proxy_id": account.proxy_id},
        )

    async def release_proxy_lock(self, proxy: Proxy):
        proxy.locked_until = None  # type: ignore
        proxy.lock_session = None  # type: ignore
        await proxy.save(update_fields=["locked_until", "lock_session"])
        self._add_log(Status.INFO, "Proxy lock released", {"proxy_id": proxy.id})

    async def _assign_proxy(self, account: Account, proxy: Proxy):
        async with in_transaction() as conn:
            account.proxy = proxy
            await account.save(update_fields=["proxy_id"], using_db=conn)
            await self.release_proxy_lock(proxy)

    async def acquire_proxy(self, country: str) -> Optional[Proxy]:
        for _ in range(1, self.MAX_RETRIES + 1):
            proxy = await self._get_free_proxy(country)
            if not proxy:
                self._add_log(
                    Status.ERROR,
                    "No available proxies for user/country",
                    {"user_id": self.user_id, "country": country},
                )
                return None
            else:
                if await self._check_proxy(proxy):
                    # не разлочиваем, разлочим в assign_proxy
                    return proxy
                else:
                    await self.release_proxy_lock(proxy)
                    continue

        self._add_log(
            Status.ERROR,
            "No working proxies for user/country",
            {"user_id": self.user_id, "country": country},
        )
        return None

    async def verify_proxy(self, account: Account) -> Optional[Proxy]:
        if account.proxy:
            proxy = account.proxy
            ok = await self._check_proxy(proxy)
            if not ok:
                if proxy.failures >= self.MAX_FAILURES:
                    await self._deactivate_account(account)
                return None
            return proxy

        proxy = await self.acquire_proxy(account.country)
        if proxy:
            await self._assign_proxy(account, proxy)
            return proxy

        return None
