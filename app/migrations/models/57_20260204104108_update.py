from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ALTER COLUMN "ref_code" TYPE VARCHAR(8) USING "ref_code"::VARCHAR(8);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ALTER COLUMN "ref_code" TYPE VARCHAR(6) USING "ref_code"::VARCHAR(6);"""
