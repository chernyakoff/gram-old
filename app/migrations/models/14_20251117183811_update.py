from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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


MODELS_STATE = (
    "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"
)
