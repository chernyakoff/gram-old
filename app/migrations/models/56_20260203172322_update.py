from tortoise import BaseDBAsyncClient


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
        FOREIGN KEY ("referred_by_id") REFERENCES "users" ("id") ON DELETE SET NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_users_ref_code";
        ALTER TABLE "users" DROP CONSTRAINT IF EXISTS "fk_users_users_referred_by";
        ALTER TABLE "users" DROP COLUMN "referred_by_id";
        ALTER TABLE "users" DROP COLUMN "ref_code";
    """
