from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "out_daily_limit" INT NOT NULL DEFAULT 6;
        ALTER TABLE "projects" DROP COLUMN "out_daily_limit";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "out_daily_limit";
        ALTER TABLE "projects" ADD "out_daily_limit" INT NOT NULL DEFAULT 6;"""
