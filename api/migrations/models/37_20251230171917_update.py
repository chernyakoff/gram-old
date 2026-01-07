from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_work_intervals" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "time_from" TIMETZ NOT NULL,
    "time_to" TIMETZ NOT NULL,
    "work_day_id" INT NOT NULL REFERENCES "user_work_days" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "user_work_intervals";"""
