from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" ADD "morning_reminder" TEXT;
        ALTER TABLE "projects" ADD "use_calendar" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "projects" ADD "meeting_reminder" TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" DROP COLUMN "morning_reminder";
        ALTER TABLE "projects" DROP COLUMN "use_calendar";
        ALTER TABLE "projects" DROP COLUMN "meeting_reminder";"""
