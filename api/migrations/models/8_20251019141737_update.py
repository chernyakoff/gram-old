from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" ADD "account_id" BIGINT;

        UPDATE "dialogs"
        SET account_id = a.id
        FROM recipients r
        JOIN mailings m ON r.mailing_id = m.id
        JOIN accounts a ON a.user_id = m.user_id
        WHERE dialogs.recipient_id = r.id;

        ALTER TABLE "dialogs" ALTER COLUMN "account_id" SET NOT NULL;

        ALTER TABLE "dialogs" ADD CONSTRAINT "fk_dialogs_accounts_652ef8f0"
        FOREIGN KEY ("account_id") REFERENCES "accounts" ("id") ON DELETE CASCADE;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" DROP CONSTRAINT IF EXISTS "fk_dialogs_accounts_652ef8f0";
        ALTER TABLE "dialogs" DROP COLUMN "account_id";"""
