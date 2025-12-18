from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" ALTER COLUMN "send_time_start" SET DEFAULT 10;
        ALTER TABLE "projects" ALTER COLUMN "send_time_end" SET DEFAULT 21;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" ALTER COLUMN "send_time_start" SET DEFAULT 0;
        ALTER TABLE "projects" ALTER COLUMN "send_time_end" SET DEFAULT 23;"""
