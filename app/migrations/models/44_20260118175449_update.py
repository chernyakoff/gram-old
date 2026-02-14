from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "project_files" ADD "status" VARCHAR(8);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "project_files" DROP COLUMN "status";"""
