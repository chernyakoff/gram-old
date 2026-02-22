from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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


MODELS_STATE = (
    "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"
)
