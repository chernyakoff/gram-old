from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "mailings" ADD "user_id" BIGINT NOT NULL;
        ALTER TABLE "mailings" ADD CONSTRAINT "fk_mailings_users_715f3d02" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "mailings" DROP CONSTRAINT IF EXISTS "fk_mailings_users_715f3d02";
        ALTER TABLE "mailings" DROP COLUMN "user_id";"""
