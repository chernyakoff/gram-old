from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "last_dialog_date" DATE;
        ALTER TABLE "accounts" ADD "first_dialog_date" DATE;
        ALTER TABLE "accounts" ADD "active_days_count" INT NOT NULL DEFAULT 0;
        COMMENT ON COLUMN "accounts"."out_daily_limit" IS 'Исходящих сообщений с одного аккаунта в сутки( deprecated)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "last_dialog_date";
        ALTER TABLE "accounts" DROP COLUMN "first_dialog_date";
        ALTER TABLE "accounts" DROP COLUMN "active_days_count";
        COMMENT ON COLUMN "accounts"."out_daily_limit" IS 'Исходящих сообщений с одного аккаунта в сутки';"""
