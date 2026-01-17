from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "status" VARCHAR(64) NOT NULL DEFAULT 'good';
        ALTER TABLE "accounts" ADD "muted_until" TIMESTAMPTZ;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "status";
        ALTER TABLE "accounts" DROP COLUMN "muted_until";"""
