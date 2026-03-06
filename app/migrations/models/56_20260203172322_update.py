from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 1. Добавляем колонку referred_by_id
        ALTER TABLE "users" ADD COLUMN "referred_by_id" BIGINT;

        -- 2. Добавляем колонку ref_code с временным nullable
        ALTER TABLE "users" ADD COLUMN "ref_code" VARCHAR(8);

        -- 3. Проставляем уникальные коды всем существующим пользователям
        -- Используем md5(random()::text) и берем 8 символов для снижения коллизий
        UPDATE "users"
        SET ref_code = substring(md5(random()::text), 1, 8);

        -- 4. Делаем колонку NOT NULL
        ALTER TABLE "users" ALTER COLUMN "ref_code" SET NOT NULL;

        -- 5. Создаем уникальный индекс
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_users_ref_code" ON "users" ("ref_code");

        -- 6. Добавляем внешний ключ
        ALTER TABLE "users"
        ADD CONSTRAINT "fk_users_users_referred_by"
        FOREIGN KEY ("referred_by_id") REFERENCES "users" ("id") ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_users_ref_code";
        ALTER TABLE "users" DROP CONSTRAINT IF EXISTS "fk_users_users_referred_by";
        ALTER TABLE "users" DROP COLUMN "referred_by_id";
        ALTER TABLE "users" DROP COLUMN "ref_code";"""


MODELS_STATE = (
    "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"
    "fVl5gnmh4HictWvNr/8Din5olA=="
)
