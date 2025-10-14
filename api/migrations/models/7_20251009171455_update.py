from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "messages" ALTER COLUMN "sender" TYPE VARCHAR(9) USING "sender"::VARCHAR(9);
        COMMENT ON COLUMN "messages"."sender" IS 'ACCOUNT: account
RECIPIENT: recipient
SYSTEM: system';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "messages" ALTER COLUMN "sender" TYPE VARCHAR(32) USING "sender"::VARCHAR(32);
        COMMENT ON COLUMN "messages"."sender" IS NULL;"""
