from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" ADD "project_id" INT;
        ALTER TABLE "accounts" ADD CONSTRAINT "fk_accounts_projects_bdf32d5a" FOREIGN KEY ("project_id") REFERENCES "projects" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "accounts" DROP CONSTRAINT IF EXISTS "fk_accounts_projects_bdf32d5a";
        ALTER TABLE "accounts" DROP COLUMN "project_id";"""
