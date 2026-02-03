from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
UPDATE accounts
SET daily_limit_left = CASE
    WHEN premium = false THEN 1
    WHEN active_days_count >= 9 THEN out_daily_limit
    ELSE
        CASE active_days_count
            WHEN 0 THEN 2
            WHEN 1 THEN 2
            WHEN 2 THEN 3
            WHEN 3 THEN 4
            WHEN 4 THEN 4
            WHEN 5 THEN 5
            WHEN 6 THEN 6
            WHEN 7 THEN 6
            WHEN 8 THEN 7
        END
END;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
