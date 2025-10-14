from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE TABLE IF NOT EXISTS "mailings" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "name" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "started_at" TIMESTAMPTZ,
    "finished_at" TIMESTAMPTZ,
    "status" VARCHAR(9) NOT NULL DEFAULT 'draft',
    "project_id" INT NOT NULL REFERENCES "projects" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "mailings"."status" IS 'DRAFT: draft\nRUNNING: running\nFINISHED: finished\nCANCELLED: cancelled';

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
COMMENT ON COLUMN "recipients"."status" IS 'PENDING: pending\nPROCESSING: processing\nSENT: sent\nFAILED: failed\nBOUNCED: bounced';
CREATE TABLE IF NOT EXISTS "recipient_account_links" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "tg_id" BIGINT NOT NULL,
    "access_hash" BIGINT NOT NULL,
    "username" VARCHAR(64),
    "phone" VARCHAR(32),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "account_id" BIGINT NOT NULL REFERENCES "accounts" ("id") ON DELETE CASCADE,
    "recipient_id" BIGINT NOT NULL REFERENCES "recipients" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_recipient_a_recipie_9eea71" UNIQUE ("recipient_id", "account_id")
);
CREATE TABLE IF NOT EXISTS "dialogs" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(6) NOT NULL DEFAULT 'init',
    "started_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "finished_at" TIMESTAMPTZ,
    "recipient_account_link_id" BIGINT NOT NULL REFERENCES "recipient_account_links" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "dialogs"."status" IS 'INIT: init\nENGAGE: engage\nOFFER: offer\nCLOSE: close';
CREATE TABLE IF NOT EXISTS "messages" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "sender" VARCHAR(32) NOT NULL,
    "tg_message_id" BIGINT,
    "text" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "dialog_id" BIGINT NOT NULL REFERENCES "dialogs" ("id") ON DELETE CASCADE
);
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "mailings";
        DROP TABLE IF EXISTS "messages";
        DROP TABLE IF EXISTS "recipient_account_links";
        DROP TABLE IF EXISTS "recipients";
        DROP TABLE IF EXISTS "dialogs";"""
