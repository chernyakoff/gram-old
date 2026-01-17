from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE EXTENSION IF NOT EXISTS vector;
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
    return "DROP TABLE IF EXISTS knowledge_chunks;"
