from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD CONSTRAINT "fk_accounts_proxies_23e7737a" FOREIGN KEY ("last_proxy_id") REFERENCES "proxies" ("id") ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP CONSTRAINT IF EXISTS "fk_accounts_proxies_23e7737a";"""
