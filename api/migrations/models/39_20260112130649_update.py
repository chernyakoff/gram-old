from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "muted_accounts" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGINT NOT NULL PRIMARY KEY,
    "username" VARCHAR(34),
    "first_name" VARCHAR(64),
    "last_name" VARCHAR(64),
    "phone" VARCHAR(32),
    "twofa" VARCHAR(64),
    "app_id" INT NOT NULL,
    "app_hash" VARCHAR(64) NOT NULL,
    "session" TEXT NOT NULL,
    "device_model" VARCHAR(64),
    "system_version" VARCHAR(64),
    "app_version" VARCHAR(64)
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "muted_accounts";"""
