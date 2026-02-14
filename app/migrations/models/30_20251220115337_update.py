from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "ai_models" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" VARCHAR(256) NOT NULL PRIMARY KEY,
    "name" VARCHAR(256) NOT NULL,
    "description" TEXT NOT NULL,
    "prompt_price" DECIMAL(20,12) NOT NULL DEFAULT 0,
    "completion_price" DECIMAL(20,12) NOT NULL DEFAULT 0
);
        ALTER TABLE "dialogs" DROP COLUMN "recipient_access_hash";
        ALTER TABLE "dialogs" DROP COLUMN "recipient_peer_id";
        ALTER TABLE "users" ADD "or_api_key" VARCHAR(256);
        ALTER TABLE "users" ADD "balance" BIGINT NOT NULL DEFAULT 0;
        ALTER TABLE "users" ADD "or_api_hash" VARCHAR(256);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "or_api_key";
        ALTER TABLE "users" DROP COLUMN "balance";
        ALTER TABLE "users" DROP COLUMN "or_api_hash";
        ALTER TABLE "dialogs" ADD "recipient_access_hash" BIGINT;
        ALTER TABLE "dialogs" ADD "recipient_peer_id" BIGINT;
        DROP TABLE IF EXISTS "ai_models";"""
