from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "meetings" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "start_at" TIMESTAMPTZ NOT NULL,
    "end_at" TIMESTAMPTZ NOT NULL,
    "status" VARCHAR(16) NOT NULL DEFAULT 'scheduled',
    "source" VARCHAR(16) NOT NULL DEFAULT 'auto',
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    "dialog_id" BIGINT NOT NULL UNIQUE REFERENCES "dialogs" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_meetings_status_d8cdb3" ON "meetings" ("status");
CREATE INDEX IF NOT EXISTS "idx_meetings_user_id_18767e" ON "meetings" ("user_id", "start_at");
CREATE INDEX IF NOT EXISTS "idx_meetings_user_id_0cdb28" ON "meetings" ("user_id", "end_at");
COMMENT ON COLUMN "meetings"."status" IS 'SCHEDULED: scheduled
CANCELLED: cancelled
COMPLETED: completed';
COMMENT ON COLUMN "meetings"."source" IS 'MANUAL: manual
API: api
AUTO: auto';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "meetings";"""


MODELS_STATE = (
    "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"
    "AcS6LztPsC4UgLCu3Wv++T+VLd9j"
)
