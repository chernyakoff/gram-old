from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGINT NOT NULL PRIMARY KEY,
    "username" VARCHAR(64),
    "first_name" VARCHAR(64),
    "last_name" VARCHAR(64),
    "photo_url" VARCHAR(256),
    "role" SMALLINT NOT NULL DEFAULT 0,
    "license_end_date" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_users_usernam_266d85" ON "users" ("username");
COMMENT ON COLUMN "users"."role" IS 'USER: 0\nADMIN: 7';
CREATE TABLE IF NOT EXISTS "accounts" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGINT NOT NULL PRIMARY KEY,
    "username" VARCHAR(34),
    "first_name" VARCHAR(64),
    "last_name" VARCHAR(64),
    "phone" VARCHAR(32),
    "about" VARCHAR(70),
    "channel" VARCHAR(34),
    "twofa" VARCHAR(64),
    "app_id" INT NOT NULL,
    "app_hash" VARCHAR(64) NOT NULL,
    "session" TEXT NOT NULL,
    "device_model" VARCHAR(64),
    "system_version" VARCHAR(64),
    "app_version" VARCHAR(64),
    "active" BOOL NOT NULL DEFAULT True,
    "busy" BOOL NOT NULL DEFAULT False,
    "premium" BOOL NOT NULL DEFAULT False,
    "country" VARCHAR(2) NOT NULL,
    "timeout_expires_at" TIMESTAMPTZ,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_accounts_id_3abbae" UNIQUE ("id", "user_id")
);
CREATE TABLE IF NOT EXISTS "account_photos" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tg_id" BIGINT NOT NULL,
    "path" VARCHAR(128) NOT NULL UNIQUE,
    "main" BOOL NOT NULL DEFAULT False,
    "access_hash" BIGINT NOT NULL,
    "file_reference" BYTEA NOT NULL,
    "account_id" BIGINT REFERENCES "accounts" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "proxies" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "host" VARCHAR(64) NOT NULL,
    "port" INT NOT NULL,
    "username" VARCHAR(255) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "active" BOOL NOT NULL DEFAULT True,
    "country" VARCHAR(2) NOT NULL,
    "locked_until" TIMESTAMPTZ,
    "lock_session" VARCHAR(36),
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_proxies_host_30bab3" UNIQUE ("host", "port", "username", "password")
);
CREATE TABLE IF NOT EXISTS "settings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "section" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "value" TEXT,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_settings_user_id_b5cfea" UNIQUE ("user_id", "section", "name")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
