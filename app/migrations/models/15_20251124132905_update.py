from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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


MODELS_STATE = (
    "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"
    "vNALeY4RGyBa+lmVpT//Dw3Mi6Q="
)
