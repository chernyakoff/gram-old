from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "meeting_duration" INT NOT NULL DEFAULT 30;
        CREATE TABLE IF NOT EXISTS "user_disabled_month_day" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "day" INT NOT NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_disabl_user_id_f919ab" UNIQUE ("user_id", "day")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "meeting_duration";
        DROP TABLE IF EXISTS "user_disabled_month_day";"""
