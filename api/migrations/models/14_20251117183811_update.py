from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "briefs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "description" TEXT NOT NULL,
    "offer" TEXT NOT NULL,
    "client" TEXT NOT NULL,
    "pains" TEXT NOT NULL,
    "advantages" TEXT NOT NULL,
    "mission" TEXT NOT NULL,
    "focus" TEXT NOT NULL,
    "project_id" INT NOT NULL UNIQUE REFERENCES "projects" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "briefs";"""
