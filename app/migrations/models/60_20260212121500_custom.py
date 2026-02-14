from tortoise import BaseDBAsyncClient


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
        ALTER TABLE "users" DROP COLUMN IF EXISTS "meeting_duration";
    """


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
        DROP TABLE IF EXISTS "user_schedules";
    """
