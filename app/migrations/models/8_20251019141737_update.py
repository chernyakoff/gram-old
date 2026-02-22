from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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
        FOREIGN KEY ("account_id") REFERENCES "accounts" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "dialogs" DROP CONSTRAINT IF EXISTS "fk_dialogs_accounts_652ef8f0";
        ALTER TABLE "dialogs" DROP COLUMN "account_id";"""


MODELS_STATE = (
    "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"
)
