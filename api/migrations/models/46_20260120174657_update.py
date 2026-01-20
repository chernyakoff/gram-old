from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "project_documents" DROP COLUMN "title";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "project_documents" ADD "title" VARCHAR(255);"""
