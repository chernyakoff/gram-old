from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "knowledge_chunks";

DROP TABLE IF EXISTS "project_documents";

CREATE TABLE IF NOT EXISTS "project_documents" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255),
    "filename" VARCHAR(255),
    "content_type" VARCHAR(100),
    "source_type" VARCHAR(4) NOT NULL DEFAULT 'file',
    "error_message" TEXT,
    "file_size" BIGINT,
    "text_length" INT,
    "chunks_count" INT,
    "source_url" VARCHAR(2048),
    "storage_path" VARCHAR(1024),
    "project_id" INT NOT NULL REFERENCES "projects" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_project_doc_source__069b92" ON "project_documents" ("source_type");
CREATE INDEX IF NOT EXISTS "idx_project_doc_project_7028da" ON "project_documents" ("project_id");
COMMENT ON COLUMN "project_documents"."source_type" IS 'FILE: file
URL: url
TEXT: text';

CREATE TABLE IF NOT EXISTS "project_files" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255),
    "filename" VARCHAR(255),
    "content_type" VARCHAR(100),
    "file_size" BIGINT,
    "storage_path" VARCHAR(1024),
    "project_id" INT NOT NULL REFERENCES "projects" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_project_fil_project_dc3e11" ON "project_files" ("project_id");
CREATE TABLE knowledge_chunks (
        id BIGSERIAL PRIMARY KEY,
        project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        document_id BIGINT NOT NULL REFERENCES project_documents(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        embedding VECTOR(1536),
        metadata JSONB,
        created_at TIMESTAMP DEFAULT now()
    );

CREATE INDEX idx_chunks_embedding
        ON knowledge_chunks
        USING ivfflat (embedding vector_cosine_ops);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "knowledge_chunks";
        DROP TABLE IF EXISTS "project_documents";
        DROP TABLE IF EXISTS "project_files";"""


MODELS_STATE = (
    "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"
)
