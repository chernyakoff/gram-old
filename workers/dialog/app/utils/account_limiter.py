from datetime import date
from typing import Optional

from app.common.models import enums, orm


class AccountLimiter:
    def __init__(
        self, account: orm.Account, daily_limit_progression: Optional[list[int]] = None
    ):
        self.account = account

    async def _get_counter(
        self, action: enums.AccountAction, target_date: date | None = None
    ) -> orm.AccountActionCounter:
        """Получает или создает счетчик для действия"""
        if target_date is None:
            target_date = date.today()

        counter, _ = await orm.AccountActionCounter.get_or_create(
            account=self.account,
            action=action,
            date=target_date,
            defaults={"count": 0},
        )
        return counter

    def _get_action_limit(self, action: enums.AccountAction) -> int:
        """Возвращает лимит для действия (динамический для NEW_DIALOG)"""
        if action == enums.AccountAction.NEW_DIALOG:
            # Динамический лимит на основе активных дней
            return self.account.get_dynamic_daily_limit()
        elif action == enums.AccountAction.RESOLVE_USERNAME:
            return 200
        else:
            # Для других действий можно добавить свои лимиты
            return 100

    async def can_perform(self, action: enums.AccountAction) -> tuple[bool, int]:
        """
        Проверяет, можно ли выполнить действие

        Returns:
            (can_perform, remaining) - можно ли выполнить и сколько осталось
        """
        counter = await self._get_counter(action)
        limit = self._get_action_limit(action)
        remaining = max(0, limit - counter.count)
        return (remaining > 0, remaining)

    async def increment(self, action: enums.AccountAction) -> bool:
        """
        Увеличивает счетчик действия

        Для NEW_DIALOG также увеличивает active_days_count при первом диалоге дня

        Returns:
            True если успешно, False если превышен лимит
        """
        counter = await self._get_counter(action)
        limit = self._get_action_limit(action)

        if counter.count >= limit:
            return False

        # Увеличиваем счетчик действия
        counter.count += 1
        await counter.save(update_fields=["count"])

        # Для NEW_DIALOG увеличиваем active_days_count при первом диалоге дня
        if action == enums.AccountAction.NEW_DIALOG:
            await self.increment_active_days()

        return True

    async def increment_active_days(self):
        """
        Увеличивает active_days_count только если это первый диалог сегодня
        Атомарная операция через SQL
        """
        today = date.today()

        # Атомарно обновляем только если last_dialog_date < today
        from tortoise import Tortoise

        conn = Tortoise.get_connection("default")

        rows = await conn.execute_query_dict(
            """
            UPDATE accounts
            SET active_days_count = active_days_count + 1,
                first_dialog_date = COALESCE(first_dialog_date, $2),
                last_dialog_date = $2
            WHERE id = $1
              AND (last_dialog_date IS NULL OR last_dialog_date < $2)
            RETURNING active_days_count, first_dialog_date, last_dialog_date;
            """,
            [self.account.id, today],
        )

        # Обновляем объект в памяти если что-то изменилось
        if rows:
            self.account.active_days_count = rows[0]["active_days_count"]
            self.account.first_dialog_date = rows[0]["first_dialog_date"]
            self.account.last_dialog_date = rows[0]["last_dialog_date"]

    async def decrement(self, action: enums.AccountAction) -> bool:
        """
        Уменьшает счетчик действия (для отката при ошибках)

        Returns:
            True если успешно
        """
        counter = await self._get_counter(action)
        if counter.count > 0:
            counter.count -= 1
            await counter.save(update_fields=["count"])
            return True
        return False

    async def get_stats(self, action: enums.AccountAction) -> dict:
        """Получить статистику по действию"""
        counter = await self._get_counter(action)
        limit = self._get_action_limit(action)

        return {
            "action": action.value,
            "used": counter.count,
            "limit": limit,
            "remaining": max(0, limit - counter.count),
            "date": counter.date,
        }

    async def get_all_stats(self) -> dict:
        """Получить статистику по всем действиям"""
        return {
            "account_id": self.account.id,
            "active_days_count": self.account.active_days_count,
            "first_dialog_date": self.account.first_dialog_date,
            "last_dialog_date": self.account.last_dialog_date,
            "actions": {
                "new_dialog": await self.get_stats(enums.AccountAction.NEW_DIALOG),
                "resolve_username": await self.get_stats(
                    enums.AccountAction.RESOLVE_USERNAME
                ),
            },
        }
