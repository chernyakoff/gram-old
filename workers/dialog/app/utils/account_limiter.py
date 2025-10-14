from datetime import date

from app.common.models import enums, orm

ACTION_LIMITS = {
    enums.AccountAction.RESOLVE_USERNAME: 200,
    enums.AccountAction.NEW_DIALOG: 5,
}


class AccountLimiter:
    def __init__(self, account: orm.Account):
        self.account = account

    async def _get_counter(
        self, action: enums.AccountAction
    ) -> orm.AccountActionCounter:
        counter, _ = await orm.AccountActionCounter.get_or_create(
            account=self.account,
            action=action,
            date=date.today(),
            defaults={"count": 0},
        )
        return counter

    async def can_do(self, action: enums.AccountAction) -> bool:
        counter = await self._get_counter(action)
        return counter.count < ACTION_LIMITS[action]

    async def increment(self, action: enums.AccountAction) -> bool:
        counter = await self._get_counter(action)
        if counter.count >= ACTION_LIMITS[action]:
            return False
        counter.count += 1
        await counter.save(update_fields=["count"])
        return True
