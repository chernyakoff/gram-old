from tortoise import BaseDBAsyncClient


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
