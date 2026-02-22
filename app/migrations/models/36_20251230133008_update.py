from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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
COMMENT ON COLUMN "user_work_days"."weekday" IS 'MONDAY: 1
TUESDAY: 2
WEDNESDAY: 3
THURSDAY: 4
FRIDAY: 5
SATURDAY: 6
SUNDAY: 7';
        CREATE INDEX IF NOT EXISTS "idx_dialogs_started_b5153b" ON "dialogs" ("started_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_dialogs_started_b5153b";
        ALTER TABLE "accounts" ADD "first_dialog_date" DATE;
        ALTER TABLE "accounts" ADD "active_days_count" INT NOT NULL DEFAULT 0;
        ALTER TABLE "accounts" ADD "last_dialog_date" DATE;
        ALTER TABLE "recipients" ADD "worker_id" VARCHAR(64);
        DROP TABLE IF EXISTS "user_work_days";"""


MODELS_STATE = (
    "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"
)
