from tortoise import BaseDBAsyncClient


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
COMMENT ON COLUMN "project_documents"."source_type" IS 'FILE: file\nURL: url\nTEXT: text';

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
        USING ivfflat (embedding vector_cosine_ops);
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "knowledge_chunks";
        DROP TABLE IF EXISTS "project_documents";
        DROP TABLE IF EXISTS "project_files";"""
