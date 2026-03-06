from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "premium_stopped" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "accounts" ALTER COLUMN "out_daily_limit" SET DEFAULT 1;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "premium_stopped";
        ALTER TABLE "accounts" ALTER COLUMN "out_daily_limit" SET DEFAULT 6;"""
