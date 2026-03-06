from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" RENAME COLUMN "prompt" TO "old_prompt";
        CREATE TABLE IF NOT EXISTS "prompts" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "role" TEXT NOT NULL,
    "context" TEXT NOT NULL,
    "init" TEXT NOT NULL,
    "engage" TEXT NOT NULL,
    "offer" TEXT NOT NULL,
    "closing" TEXT NOT NULL,
    "instruction" TEXT NOT NULL,
    "rules" TEXT NOT NULL,
    "transitions" TEXT NOT NULL,
    "project_id" INT NOT NULL UNIQUE REFERENCES "projects" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "projects" RENAME COLUMN "old_prompt" TO "prompt";
        DROP TABLE IF EXISTS "prompts";"""
