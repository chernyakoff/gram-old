from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" DROP CONSTRAINT IF EXISTS "fk_dialogs_recipien_45ecde90";
        ALTER TABLE "dialogs" ADD "recipient_id" BIGINT NOT NULL UNIQUE;
        ALTER TABLE "dialogs" DROP COLUMN "recipient_account_link_id";
        DROP TABLE IF EXISTS "recipient_account_links";
        ALTER TABLE "dialogs" ADD CONSTRAINT "fk_dialogs_recipien_82984074" FOREIGN KEY ("recipient_id") REFERENCES "recipients" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" DROP CONSTRAINT IF EXISTS "fk_dialogs_recipien_82984074";
        ALTER TABLE "dialogs" ADD "recipient_account_link_id" BIGINT NOT NULL;
        ALTER TABLE "dialogs" DROP COLUMN "recipient_id";
        ALTER TABLE "dialogs" ADD CONSTRAINT "fk_dialogs_recipien_45ecde90" FOREIGN KEY ("recipient_account_link_id") REFERENCES "recipient_account_links" ("id") ON DELETE CASCADE;"""
