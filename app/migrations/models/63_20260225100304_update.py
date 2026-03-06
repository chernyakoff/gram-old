from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_users_usernam_266d85";
        ALTER TABLE "users" DROP CONSTRAINT IF EXISTS "fk_users_users_daf3d01e";
        ALTER TABLE "users" DROP COLUMN "photo_url";
        ALTER TABLE "users" DROP COLUMN "first_name";
        ALTER TABLE "users" DROP COLUMN "role";
        ALTER TABLE "users" DROP COLUMN "referred_by_id";
        ALTER TABLE "users" DROP COLUMN "balance";
        ALTER TABLE "users" DROP COLUMN "or_model";
        ALTER TABLE "users" DROP COLUMN "last_name";
        ALTER TABLE "users" DROP COLUMN "license_end_date";
        ALTER TABLE "users" DROP COLUMN "username";
        ALTER TABLE "users" DROP COLUMN "or_api_key";
        ALTER TABLE "users" DROP COLUMN "or_api_hash";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "photo_url" VARCHAR(256);
        ALTER TABLE "users" ADD "first_name" VARCHAR(64);
        ALTER TABLE "users" ADD "role" SMALLINT NOT NULL DEFAULT 0;
        ALTER TABLE "users" ADD "referred_by_id" BIGINT;
        ALTER TABLE "users" ADD "balance" BIGINT NOT NULL DEFAULT 0;
        ALTER TABLE "users" ADD "or_model" VARCHAR(256);
        ALTER TABLE "users" ADD "last_name" VARCHAR(64);
        ALTER TABLE "users" ADD "license_end_date" TIMESTAMPTZ;
        ALTER TABLE "users" ADD "username" VARCHAR(34);
        ALTER TABLE "users" ADD "or_api_key" VARCHAR(256);
        ALTER TABLE "users" ADD "or_api_hash" VARCHAR(256);
        COMMENT ON COLUMN "users"."role" IS 'USER: 0\nADMIN: 7';
        ALTER TABLE "users" ADD CONSTRAINT "fk_users_users_daf3d01e" FOREIGN KEY ("referred_by_id") REFERENCES "users" ("id") ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS "idx_users_usernam_266d85" ON "users" ("username");"""


MODELS_STATE = (
    "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"
    "yXgVNaJ0yO8rLyHy8//h85aG+F"
)
