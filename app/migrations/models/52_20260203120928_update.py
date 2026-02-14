from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "active_days_count" INT NOT NULL DEFAULT 0;
        ALTER TABLE "accounts" ADD "daily_limit_left" INT NOT NULL DEFAULT 0;
        COMMENT ON COLUMN "accounts"."out_daily_limit" IS 'Исходящих сообщений с одного аккаунта в сутки';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "active_days_count";
        ALTER TABLE "accounts" DROP COLUMN "daily_limit_left";
        COMMENT ON COLUMN "accounts"."out_daily_limit" IS 'Исходящих сообщений с одного аккаунта в сутки( deprecated)';"""
