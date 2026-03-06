from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE "accounts" SET proxy_id = NULL;
        ALTER TABLE "accounts" DROP CONSTRAINT IF EXISTS "fk_accounts_proxies_e6656621";
        ALTER TABLE "accounts" ADD CONSTRAINT "fk_accounts_proxies_e6656621" FOREIGN KEY ("proxy_id") REFERENCES "proxies" ("id") ON DELETE SET NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_accounts_proxy_i_debf08" ON "accounts" ("proxy_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_accounts_proxy_i_debf08";
        ALTER TABLE "accounts" DROP CONSTRAINT IF EXISTS "fk_accounts_proxies_e6656621";
        ALTER TABLE "accounts" ADD CONSTRAINT "fk_accounts_proxies_e6656621" FOREIGN KEY ("proxy_id") REFERENCES "proxies" ("id") ON DELETE SET NULL;"""
