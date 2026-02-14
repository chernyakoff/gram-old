from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP CONSTRAINT IF EXISTS "fk_accounts_proxies_23e7737a";
        ALTER TABLE "accounts" RENAME COLUMN "last_proxy_id" TO "proxy_id";
        ALTER TABLE "accounts" DROP COLUMN "worker_id";
        COMMENT ON COLUMN "accounts"."status" IS 'GOOD: good
BANNED: banned
MUTED: muted
FROZEN: frozen
EXITED: exited
NOPROXY: noproxy';
        ALTER TABLE "accounts" ADD CONSTRAINT "fk_accounts_proxies_e6656621" FOREIGN KEY ("proxy_id") REFERENCES "proxies" ("id") ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP CONSTRAINT IF EXISTS "fk_accounts_proxies_e6656621";
        ALTER TABLE "accounts" RENAME COLUMN "proxy_id" TO "last_proxy_id";
        ALTER TABLE "accounts" ADD "worker_id" VARCHAR(64);
        COMMENT ON COLUMN "accounts"."status" IS 'GOOD: good
BANNED: banned
MUTED: muted
FROZEN: frozen
EXITED: exited';
        ALTER TABLE "accounts" ADD CONSTRAINT "fk_accounts_proxies_23e7737a" FOREIGN KEY ("last_proxy_id") REFERENCES "proxies" ("id") ON DELETE SET NULL;"""
