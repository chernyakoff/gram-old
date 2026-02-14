from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "prompts" DROP COLUMN "transitions";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "prompts" ADD "transitions" TEXT NOT NULL;"""
