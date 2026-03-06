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
OPERATOR: operator
MANUAL: manual';
        ALTER TABLE "recipients" ADD "about" VARCHAR(150);
        ALTER TABLE "recipients" ADD "channel" VARCHAR(34);
        ALTER TABLE "recipients" ADD "first_name" VARCHAR(64);
        ALTER TABLE "recipients" ADD "last_name" VARCHAR(64);
        ALTER TABLE "recipients" ADD "premium" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "recipients" ADD "phone" VARCHAR(32);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "dialogs"."status" IS 'INIT: init
ENGAGE: engage
OFFER: offer
CLOSING: closing
COMPLETE: complete
NEGATIVE: negative
OPERATOR: operator';
        ALTER TABLE "recipients" DROP COLUMN "about";
        ALTER TABLE "recipients" DROP COLUMN "channel";
        ALTER TABLE "recipients" DROP COLUMN "first_name";
        ALTER TABLE "recipients" DROP COLUMN "last_name";
        ALTER TABLE "recipients" DROP COLUMN "premium";
        ALTER TABLE "recipients" DROP COLUMN "phone";"""


MODELS_STATE = (
    "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"
)
