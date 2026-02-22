from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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
        USING ivfflat (embedding vector_cosine_ops);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS knowledge_chunks;"""


MODELS_STATE = (
    "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"
)
