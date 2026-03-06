from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP COLUMN "first_dialog_date";
        ALTER TABLE "accounts" DROP COLUMN "active_days_count";
        ALTER TABLE "accounts" DROP COLUMN "last_dialog_date";
        ALTER TABLE "recipients" DROP COLUMN "worker_id";
        CREATE TABLE IF NOT EXISTS "user_work_days" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "weekday" SMALLINT NOT NULL,
    "is_enabled" BOOL NOT NULL DEFAULT True,
    "work_from" TIMETZ,
    "work_to" TIMETZ,
    "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_work_d_user_id_504bbf" UNIQUE ("user_id", "weekday")
);
COMMENT ON COLUMN "user_work_days"."weekday" IS 'MONDAY: 1\nTUESDAY: 2\nWEDNESDAY: 3\nTHURSDAY: 4\nFRIDAY: 5\nSATURDAY: 6\nSUNDAY: 7';
        CREATE INDEX IF NOT EXISTS "idx_dialogs_started_b5153b" ON "dialogs" ("started_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_dialogs_started_b5153b";
        ALTER TABLE "accounts" ADD "first_dialog_date" DATE;
        ALTER TABLE "accounts" ADD "active_days_count" INT NOT NULL DEFAULT 0;
        ALTER TABLE "accounts" ADD "last_dialog_date" DATE;
        ALTER TABLE "recipients" ADD "worker_id" VARCHAR(64);
        DROP TABLE IF EXISTS "user_work_days";"""
