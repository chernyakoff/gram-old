from tortoise import BaseDBAsyncClient


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
COMMENT ON COLUMN "meetings"."status" IS 'SCHEDULED: scheduled\nCANCELLED: cancelled\nCOMPLETED: completed';
COMMENT ON COLUMN "meetings"."source" IS 'MANUAL: manual\nAPI: api\nAUTO: auto';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "meetings";"""
