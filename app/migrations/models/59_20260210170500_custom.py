from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "morning_reminders_sent" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            "meeting_id" INT NOT NULL REFERENCES "meetings" ("id") ON DELETE CASCADE,
            CONSTRAINT "uid_morning_reminders_sent_meeting_id" UNIQUE ("meeting_id")
        );
        CREATE TABLE IF NOT EXISTS "meeting_reminders_sent" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            "meeting_id" INT NOT NULL REFERENCES "meetings" ("id") ON DELETE CASCADE,
            CONSTRAINT "uid_meeting_reminders_sent_meeting_id" UNIQUE ("meeting_id")
        );"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "meeting_reminders_sent";
        DROP TABLE IF EXISTS "morning_reminders_sent";"""
