from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recipients" ADD "peer_id" BIGINT;
        ALTER TABLE "recipients" ADD "access_hash" BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recipients" DROP COLUMN "peer_id";
        ALTER TABLE "recipients" DROP COLUMN "access_hash";"""
