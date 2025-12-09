from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE accounts
    DROP CONSTRAINT accounts_project_id_fkey;

ALTER TABLE accounts
    ADD CONSTRAINT accounts_project_id_fkey
        FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE SET NULL;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
