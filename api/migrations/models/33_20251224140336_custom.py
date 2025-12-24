from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE INDEX IF NOT EXISTS idx_messages_dialog_created 
ON messages(dialog_id, created_at DESC);


CREATE INDEX IF NOT EXISTS idx_dialogs_status_finished 
ON dialogs(account_id, status, finished_at)
WHERE finished_at IS NULL;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
