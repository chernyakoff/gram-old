from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "account_action_counter"."action" IS 'RESOLVE_USERNAME: resolve_username
NEW_DIALOG: new_dialog';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "account_action_counter"."action" IS 'RESOLVE_USERNAME: resolve_username
SEND_MESSAGE_STRANGER: send_message_stranger';"""
