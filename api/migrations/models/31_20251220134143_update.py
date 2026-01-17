from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "app_settings" ADD "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "app_settings" ADD "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "users" ADD "or_model" VARCHAR(256);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "or_model";
        ALTER TABLE "app_settings" DROP COLUMN "created_at";
        ALTER TABLE "app_settings" DROP COLUMN "updated_at";"""
