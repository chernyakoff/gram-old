from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "dialogs"."status" IS 'INIT: init
ENGAGE: engage
OFFER: offer
CLOSING: closing
COMPLETE: complete
NEGATIVE: negative
OPERATOR: operator';
        ALTER TABLE "messages" ADD "ack" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "dialogs"."status" IS 'INIT: init
ENGAGE: engage
OFFER: offer
CLOSING: closing
COMPLETE: complete';
        ALTER TABLE "messages" DROP COLUMN "ack";"""
