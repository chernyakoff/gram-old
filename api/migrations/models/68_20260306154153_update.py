from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "mob_proxies" DROP CONSTRAINT IF EXISTS "fk_mob_prox_users_e817f45e";
        ALTER TABLE "mob_proxies" ADD CONSTRAINT "fk_mob_prox_users_e817f45e" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_mob_proxies_user_id_df9bbb" ON "mob_proxies" ("user_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_mob_proxies_user_id_df9bbb";
        ALTER TABLE "mob_proxies" DROP CONSTRAINT IF EXISTS "fk_mob_prox_users_e817f45e";
        ALTER TABLE "mob_proxies" ADD CONSTRAINT "fk_mob_prox_users_e817f45e" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;"""
