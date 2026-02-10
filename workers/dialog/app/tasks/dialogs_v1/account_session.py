from __future__ import annotations

import asyncio

from telethon import TelegramClient
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.common.utils.account import AccountUtil
from app.common.utils.proxy_pool import ProxyPool
from app.utils.logger import Logger


class AccountSession:
    """
    Manages account lifecycle:
    - proxy validation
    - Telegram client connect/authorize
    - release/cleanup
    """

    def __init__(self, account: orm.Account, logger: Logger):
        self.account = account
        self.logger = logger
        self.client: TelegramClient | None = None

    async def connect_and_authorize(self) -> bool:
        pool = ProxyPool(self.account.user_id)
        proxy = await pool.verify_proxy(self.account)
        if not proxy:
            self.logger.from_proxy_pool(pool)
            await self.release(error="No proxy")
            return False

        account_util = AccountUtil.from_orm(self.account)
        self.client = account_util.create_client(proxy)

        try:
            await asyncio.wait_for(self.client.connect(), timeout=30)
        except asyncio.TimeoutError:
            self.logger.error("Таймаут подключения клиента (30 сек)")
            await self.release(error="Client connect timeout")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка подключения клиента: {e}")
            if "used under two different IP" in str(e):
                self.logger.error(
                    "⚠️ КРИТИЧНО: Сессия использована с другого IP! Деактивируем аккаунт."
                )
                self.account.status = enums.AccountStatus.EXITED
                await self.account.save(update_fields=["status", "updated_at"])
            await self.release(error=f"Connection error: {e}")
            return False

        try:
            is_authorized = await asyncio.wait_for(
                self.client.is_user_authorized(), timeout=10
            )
            if not is_authorized:
                self.account.status = enums.AccountStatus.EXITED
                self.logger.error(f"Account {self.account.id} не авторизован")
                await self.release(error="Account not authorized")
                return False
        except asyncio.TimeoutError:
            self.logger.error("Таймаут проверки авторизации")
            await self.release(error="Authorization check timeout")
            return False

        self.logger.info(f"Account {self.account.id} подключен к Telegram")
        return True

    async def disconnect(self):
        if not self.client:
            await self.release()
            return

        try:
            if self.client.is_connected():
                await asyncio.wait_for(self.client.disconnect(), timeout=10)  # type: ignore
        except Exception as e:
            self.logger.error(f"Ошибка при отключении клиента: {e}")
        finally:
            await self.release()

    async def release(self, error: str | None = None):
        update_data = {
            "busy": False,
            "lease_expires_at": None,
            "last_attempt_at": tz.now(),
            "last_error": error,
        }
        self.account.update_from_dict(update_data)
        update_fields = list(update_data.keys())
        update_fields.append("status")
        update_fields.append("updated_at")
        await self.account.save(update_fields=update_fields)
