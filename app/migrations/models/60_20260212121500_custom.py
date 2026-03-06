from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_schedules" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            "name" VARCHAR(128) NOT NULL DEFAULT 'Основное',
            "timezone" VARCHAR(64) NOT NULL DEFAULT 'Europe/Moscow',
            "meeting_duration" INT NOT NULL DEFAULT 30,
            "is_default" BOOL NOT NULL DEFAULT FALSE,
            "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
            CONSTRAINT "uid_user_schedules_user_name" UNIQUE ("user_id", "name")
        );
        CREATE INDEX IF NOT EXISTS "idx_user_sched_user_default" ON "user_schedules" ("user_id", "is_default");

        INSERT INTO "user_schedules" ("name", "timezone", "meeting_duration", "is_default", "user_id", "created_at", "updated_at")
        SELECT
            'Основное',
            COALESCE("timezone", 'Europe/Moscow'),
            COALESCE("meeting_duration", 30),
            TRUE,
            "id",
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM "users"
        WHERE NOT EXISTS (
            SELECT 1 FROM "user_schedules" us WHERE us."user_id" = "users"."id"
        );

        ALTER TABLE "user_work_days" ADD COLUMN "schedule_id" INT;
        UPDATE "user_work_days" uwd
        SET "schedule_id" = us."id"
        FROM "user_schedules" us
        WHERE us."user_id" = uwd."user_id" AND us."is_default" = TRUE;
        ALTER TABLE "user_work_days" ALTER COLUMN "schedule_id" SET NOT NULL;
        ALTER TABLE "user_work_days" ADD CONSTRAINT "fk_user_work_days_schedule_id" FOREIGN KEY ("schedule_id") REFERENCES "user_schedules" ("id") ON DELETE CASCADE;
        ALTER TABLE "user_work_days" DROP CONSTRAINT IF EXISTS "uid_user_work_d_user_id_504bbf";
        ALTER TABLE "user_work_days" ADD CONSTRAINT "uid_user_work_d_schedule_weekday" UNIQUE ("schedule_id", "weekday");
        ALTER TABLE "user_work_days" DROP COLUMN "user_id";

        ALTER TABLE "user_disabled_month_day" ADD COLUMN "schedule_id" INT;
        UPDATE "user_disabled_month_day" umd
        SET "schedule_id" = us."id"
        FROM "user_schedules" us
        WHERE us."user_id" = umd."user_id" AND us."is_default" = TRUE;
        ALTER TABLE "user_disabled_month_day" ALTER COLUMN "schedule_id" SET NOT NULL;
        ALTER TABLE "user_disabled_month_day" ADD CONSTRAINT "fk_user_disabled_month_day_schedule_id" FOREIGN KEY ("schedule_id") REFERENCES "user_schedules" ("id") ON DELETE CASCADE;
        ALTER TABLE "user_disabled_month_day" DROP CONSTRAINT IF EXISTS "uid_user_disabl_user_id_f919ab";
        ALTER TABLE "user_disabled_month_day" ADD CONSTRAINT "uid_user_disabled_schedule_day" UNIQUE ("schedule_id", "day");
        ALTER TABLE "user_disabled_month_day" DROP COLUMN "user_id";

        ALTER TABLE "meetings" ADD COLUMN "schedule_id" INT;
        UPDATE "meetings" m
        SET "schedule_id" = us."id"
        FROM "user_schedules" us
        WHERE us."user_id" = m."user_id" AND us."is_default" = TRUE;
        ALTER TABLE "meetings" ALTER COLUMN "schedule_id" SET NOT NULL;
        ALTER TABLE "meetings" ADD CONSTRAINT "fk_meetings_schedule_id" FOREIGN KEY ("schedule_id") REFERENCES "user_schedules" ("id") ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS "idx_meetings_schedule_start" ON "meetings" ("schedule_id", "start_at");
        CREATE INDEX IF NOT EXISTS "idx_meetings_schedule_end" ON "meetings" ("schedule_id", "end_at");

        ALTER TABLE "users" DROP COLUMN IF EXISTS "timezone";
        ALTER TABLE "users" DROP COLUMN IF EXISTS "meeting_duration";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "timezone" VARCHAR(64) DEFAULT 'Europe/Moscow';
        ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "meeting_duration" INT NOT NULL DEFAULT 30;

        UPDATE "users" u
        SET
            "timezone" = COALESCE(us."timezone", 'Europe/Moscow'),
            "meeting_duration" = COALESCE(us."meeting_duration", 30)
        FROM "user_schedules" us
        WHERE us."user_id" = u."id" AND us."is_default" = TRUE;

        ALTER TABLE "user_work_days" ADD COLUMN "user_id" BIGINT;
        UPDATE "user_work_days" uwd
        SET "user_id" = us."user_id"
        FROM "user_schedules" us
        WHERE us."id" = uwd."schedule_id";
        ALTER TABLE "user_work_days" ALTER COLUMN "user_id" SET NOT NULL;
        ALTER TABLE "user_work_days" DROP CONSTRAINT IF EXISTS "uid_user_work_d_schedule_weekday";
        ALTER TABLE "user_work_days" ADD CONSTRAINT "uid_user_work_d_user_id_504bbf" UNIQUE ("user_id", "weekday");
        ALTER TABLE "user_work_days" DROP CONSTRAINT IF EXISTS "fk_user_work_days_schedule_id";
        ALTER TABLE "user_work_days" DROP COLUMN "schedule_id";
        ALTER TABLE "user_work_days" ADD CONSTRAINT "fk_user_work_days_user_id" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;

        ALTER TABLE "user_disabled_month_day" ADD COLUMN "user_id" BIGINT;
        UPDATE "user_disabled_month_day" umd
        SET "user_id" = us."user_id"
        FROM "user_schedules" us
        WHERE us."id" = umd."schedule_id";
        ALTER TABLE "user_disabled_month_day" ALTER COLUMN "user_id" SET NOT NULL;
        ALTER TABLE "user_disabled_month_day" DROP CONSTRAINT IF EXISTS "uid_user_disabled_schedule_day";
        ALTER TABLE "user_disabled_month_day" ADD CONSTRAINT "uid_user_disabl_user_id_f919ab" UNIQUE ("user_id", "day");
        ALTER TABLE "user_disabled_month_day" DROP CONSTRAINT IF EXISTS "fk_user_disabled_month_day_schedule_id";
        ALTER TABLE "user_disabled_month_day" DROP COLUMN "schedule_id";
        ALTER TABLE "user_disabled_month_day" ADD CONSTRAINT "fk_user_disabled_month_day_user_id" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;

        DROP INDEX IF EXISTS "idx_meetings_schedule_end";
        DROP INDEX IF EXISTS "idx_meetings_schedule_start";
        ALTER TABLE "meetings" DROP CONSTRAINT IF EXISTS "fk_meetings_schedule_id";
        ALTER TABLE "meetings" DROP COLUMN "schedule_id";

        DROP INDEX IF EXISTS "idx_user_sched_user_default";
        DROP TABLE IF EXISTS "user_schedules";"""


MODELS_STATE = (
    "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"
)
