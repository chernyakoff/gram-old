from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ai_models" ADD "visible" BOOL NOT NULL DEFAULT True;
        CREATE TABLE IF NOT EXISTS "project_documents" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255),
    "filename" VARCHAR(255),
    "content_type" VARCHAR(100),
    "source_type" VARCHAR(4) NOT NULL DEFAULT 'file',
    "status" VARCHAR(10) NOT NULL DEFAULT 'uploaded',
    "error_message" TEXT,
    "file_size" BIGINT,
    "text_length" INT,
    "chunks_count" INT,
    "source_url" VARCHAR(2048),
    "storage_path" VARCHAR(1024),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "processed_at" TIMESTAMPTZ,
    "project_id" INT NOT NULL REFERENCES "projects" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_project_doc_source__069b92" ON "project_documents" ("source_type");
CREATE INDEX IF NOT EXISTS "idx_project_doc_status_9e6890" ON "project_documents" ("status");
CREATE INDEX IF NOT EXISTS "idx_project_doc_project_7028da" ON "project_documents" ("project_id");
CREATE INDEX IF NOT EXISTS "idx_project_doc_project_5feb34" ON "project_documents" ("project_id", "status");
COMMENT ON COLUMN "project_documents"."source_type" IS 'FILE: file\nURL: url\nTEXT: text';
COMMENT ON COLUMN "project_documents"."status" IS 'UPLOADED: uploaded\nPROCESSING: processing\nREADY: ready\nFAILED: failed';
COMMENT ON TABLE "project_documents" IS 'Документ, загруженный пользователем в рамках проекта.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "ai_models" DROP COLUMN "visible";
        DROP TABLE IF EXISTS "project_documents";"""
