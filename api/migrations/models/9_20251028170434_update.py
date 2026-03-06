from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "app_settings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "section" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "value" TEXT,
    CONSTRAINT "uid_app_setting_section_5cfa7d" UNIQUE ("section", "name")
);
CREATE INDEX IF NOT EXISTS "idx_app_setting_section_5cfa7d" ON "app_settings" ("section", "name");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "app_settings";"""
