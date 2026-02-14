from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
UPDATE accounts a
SET active_days_count = sub.days_count
FROM (
    SELECT
        account_id,
        COUNT(DISTINCT DATE(started_at)) AS days_count
    FROM dialogs
    GROUP BY account_id
) sub
WHERE a.id = sub.account_id;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
