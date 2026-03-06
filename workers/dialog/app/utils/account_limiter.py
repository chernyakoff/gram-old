from datetime import date
from typing import Optional

from app.common.models import enums, orm


class AccountLimiter:
    def __init__(self, account: orm.Account):
        self.account = account

    async def _get_counter(
        self, action: enums.AccountAction, target_date: date | None = None
    ) -> orm.AccountActionCounter:
        if target_date is None:
            target_date = date.today()

        counter, _ = await orm.AccountActionCounter.get_or_create(
            account=self.account,
            action=action,
            date=target_date,
            defaults={"count": 0},
        )
        return counter

    async def _get_action_limit(self, action: enums.AccountAction) -> int:
        """Возвращает лимит для действия"""
        if action == enums.AccountAction.NEW_DIALOG:
            # Динамический лимит на основе активных дней
            return await self.account.get_dynamic_daily_limit()
        elif action == enums.AccountAction.RESOLVE_USERNAME:
            return 200
        else:
            return 100

    async def can_perform(self, action: enums.AccountAction) -> tuple[bool, int]:
        """Проверяет, можно ли выполнить действие"""
        counter = await self._get_counter(action)
        limit = await self._get_action_limit(action)
        remaining = max(0, limit - counter.count)
        return (remaining > 0, remaining)

    async def decrement(self, action: enums.AccountAction) -> bool:
        """Уменьшает счетчик действия (для отката при ошибках)"""
        counter = await self._get_counter(action)
        if counter.count > 0:
            counter.count -= 1
            await counter.save(update_fields=["count"])
            return True
        return False

    async def get_stats(self, action: enums.AccountAction) -> dict:
        """Получить статистику по действию"""
        counter = await self._get_counter(action)
        limit = await self._get_action_limit(action)

        return {
            "action": action.value,
            "used": counter.count,
            "limit": limit,
            "remaining": max(0, limit - counter.count),
            "date": counter.date,
        }

    async def get_all_stats(self) -> dict:
        """Получить статистику по всем действиям"""
        active_days = await self.account.get_active_days_count()

        return {
            "account_id": self.account.id,
            "active_days_count": active_days,
            "actions": {
                "new_dialog": await self.get_stats(enums.AccountAction.NEW_DIALOG),
                "resolve_username": await self.get_stats(
                    enums.AccountAction.RESOLVE_USERNAME
                ),
            },
        }
