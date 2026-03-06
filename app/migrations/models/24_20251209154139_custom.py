from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE accounts
    DROP CONSTRAINT accounts_project_id_fkey;

ALTER TABLE accounts
    ADD CONSTRAINT accounts_project_id_fkey
        FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "k="
)
