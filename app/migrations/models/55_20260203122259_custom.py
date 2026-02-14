from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
UPDATE accounts a
SET daily_limit_left = GREATEST(
    0,
    a.daily_limit_left - COALESCE(c.count, 0)
)
FROM account_action_counter c
WHERE a.id = c.account_id
  AND c.action = 'new_dialog'
  AND c.date = CURRENT_DATE;

        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
