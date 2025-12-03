from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ALTER COLUMN "about" TYPE VARCHAR(150) USING "about"::VARCHAR(150);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ALTER COLUMN "about" TYPE VARCHAR(70) USING "about"::VARCHAR(70);"""
