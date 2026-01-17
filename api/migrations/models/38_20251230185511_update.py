from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "timezone" VARCHAR(64) DEFAULT 'Europe/Moscow';
        ALTER TABLE "user_work_days" DROP COLUMN "work_from";
        ALTER TABLE "user_work_days" DROP COLUMN "work_to";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "timezone";
        ALTER TABLE "user_work_days" ADD "work_from" TIMETZ;
        ALTER TABLE "user_work_days" ADD "work_to" TIMETZ;"""
