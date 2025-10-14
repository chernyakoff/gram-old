from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "lease_expires_at" TIMESTAMPTZ;
        ALTER TABLE "accounts" ADD "worker_id" VARCHAR(64);
        ALTER TABLE "accounts" ADD "last_attempt_at" TIMESTAMPTZ;
        ALTER TABLE "accounts" ADD "last_error" TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "lease_expires_at";
        ALTER TABLE "accounts" DROP COLUMN "worker_id";
        ALTER TABLE "accounts" DROP COLUMN "last_attempt_at";
        ALTER TABLE "accounts" DROP COLUMN "last_error";"""
