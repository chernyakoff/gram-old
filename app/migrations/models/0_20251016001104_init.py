from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGINT NOT NULL PRIMARY KEY,
    "username" VARCHAR(34),
    "first_name" VARCHAR(64),
    "last_name" VARCHAR(64),
    "photo_url" VARCHAR(256),
    "role" SMALLINT NOT NULL DEFAULT 0,
    "license_end_date" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_users_usernam_266d85" ON "users" ("username");
COMMENT ON COLUMN "users"."role" IS 'USER: 0
ADMIN: 7';
CREATE TABLE IF NOT EXISTS "projects" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL,
    "status" BOOL NOT NULL DEFAULT True,
    "dialog_limit" INT NOT NULL DEFAULT 10,
    "out_daily_limit" INT NOT NULL DEFAULT 6,
    "send_time_start" INT NOT NULL DEFAULT 0,
    "send_time_end" INT NOT NULL DEFAULT 23,
    "first_message" TEXT NOT NULL,
    "prompt" TEXT NOT NULL,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "projects"."dialog_limit" IS 'Сообщений в одной переписке';
COMMENT ON COLUMN "projects"."out_daily_limit" IS 'Исходящих сообщений с одного аккаунта в сутки';
COMMENT ON COLUMN "projects"."send_time_start" IS 'Начало времени рассылки';
COMMENT ON COLUMN "projects"."send_time_end" IS 'Конец времени рассылки';
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
    "worker_id" VARCHAR(64),
    "lease_expires_at" TIMESTAMPTZ,
    "last_error" TEXT,
    "last_attempt_at" TIMESTAMPTZ,
    "project_id" INT REFERENCES "projects" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_accounts_id_3abbae" UNIQUE ("id", "user_id")
);
CREATE TABLE IF NOT EXISTS "account_action_counter" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "action" VARCHAR(64) NOT NULL,
    "date" DATE NOT NULL,
    "count" INT NOT NULL DEFAULT 0,
    "account_id" BIGINT NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_account_act_account_e7e16e" UNIQUE ("account_id", "action", "date")
);
COMMENT ON COLUMN "account_action_counter"."action" IS 'RESOLVE_USERNAME: resolve_username
NEW_DIALOG: new_dialog';
CREATE TABLE IF NOT EXISTS "account_photos" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tg_id" BIGINT NOT NULL,
    "path" VARCHAR(128) NOT NULL UNIQUE,
    "main" BOOL NOT NULL DEFAULT False,
    "access_hash" BIGINT NOT NULL,
    "file_reference" BYTEA NOT NULL,
    "account_id" BIGINT REFERENCES "accounts" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "mailings" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "started_at" TIMESTAMPTZ,
    "finished_at" TIMESTAMPTZ,
    "status" VARCHAR(9) NOT NULL DEFAULT 'draft',
    "project_id" INT NOT NULL REFERENCES "projects" ("id") ON DELETE CASCADE,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "mailings"."status" IS 'DRAFT: draft
RUNNING: running
FINISHED: finished
CANCELLED: cancelled';
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
CREATE TABLE IF NOT EXISTS "recipients" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "username" VARCHAR(320) NOT NULL,
    "metadata" JSONB,
    "status" VARCHAR(10) NOT NULL DEFAULT 'pending',
    "worker_id" VARCHAR(64),
    "lease_expires_at" TIMESTAMPTZ,
    "attempts" INT NOT NULL DEFAULT 0,
    "last_error" TEXT,
    "last_attempt_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "mailing_id" BIGINT NOT NULL REFERENCES "mailings" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_recipients_mailing_fcf65c" ON "recipients" ("mailing_id", "status", "lease_expires_at");
CREATE INDEX IF NOT EXISTS "idx_recipients_lease_e_06a290" ON "recipients" ("lease_expires_at");
COMMENT ON COLUMN "recipients"."status" IS 'PENDING: pending
PROCESSING: processing
SENT: sent
FAILED: failed
BOUNCED: bounced';
CREATE TABLE IF NOT EXISTS "dialogs" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(6) NOT NULL DEFAULT 'init',
    "started_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "finished_at" TIMESTAMPTZ,
    "recipient_id" BIGINT NOT NULL UNIQUE REFERENCES "recipients" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "dialogs"."status" IS 'INIT: init
ENGAGE: engage
OFFER: offer
CLOSE: close';
CREATE TABLE IF NOT EXISTS "messages" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "sender" VARCHAR(9) NOT NULL,
    "tg_message_id" BIGINT,
    "text" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "dialog_id" BIGINT NOT NULL REFERENCES "dialogs" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "messages"."sender" IS 'ACCOUNT: account
RECIPIENT: recipient
SYSTEM: system';
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


MODELS_STATE = (
    "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"
    "OR"
)
