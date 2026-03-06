from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" ADD "recipient_access_hash" BIGINT;
        ALTER TABLE "dialogs" ADD "recipient_peer_id" BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" DROP COLUMN "recipient_access_hash";
        ALTER TABLE "dialogs" DROP COLUMN "recipient_peer_id";"""
