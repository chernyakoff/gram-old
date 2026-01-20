import asyncio
import os
import re
from datetime import timedelta
from typing import Sequence

import tiktoken
from hatchet_sdk import Context
from pydantic import BaseModel
from tortoise import Tortoise

from app.client import hatchet
from app.common.models import orm
from app.common.utils import openrouter
from app.common.utils.s3 import AsyncS3Client
from app.common.utils.usd_rate import get_usd_rate
from app.config import config
from app.utils.stream_logger import StreamLogger

enc = tiktoken.get_encoding("cl100k_base")

HEADER_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)

EMBED_MODEL = "openai/text-embedding-3-small"


class ProjectDocument(BaseModel):
    filename: str
    file_size: int
    storage_path: str
    content_type: str


class ProjectDocumentFull(BaseModel):
    filename: str
    file_size: int
    storage_path: str
    content_type: str
    content: str


class ProjectDocumentsIn(BaseModel):
    project_id: int
    documents: list[ProjectDocument]


async def fetch_file(document: ProjectDocument) -> ProjectDocumentFull:
    async with AsyncS3Client() as s3:  # type: ignore
        content_bytes = await s3.get(document.storage_path)
    params = document.model_dump()
    params["content"] = content_bytes.decode("utf-8")  # предполагаем, что UTF-8 текст
    return ProjectDocumentFull(**params)


async def fetch_all(documents: list[ProjectDocument]) -> list[ProjectDocumentFull]:
    tasks = [fetch_file(d) for d in documents]
    return await asyncio.gather(*tasks)  # возвращает список строк


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*(---|\*\*\*)\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def split_blocks(text: str) -> list[str]:
    headers = HEADER_RE.findall(text)
    if headers:
        blocks = HEADER_RE.split(text)
        return [b.strip() for b in blocks if b.strip()]
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_text(
    text: str,
    min_tokens=200,
    max_tokens=700,
    overlap=120,
):
    text = normalize(text)
    blocks = split_blocks(text)

    chunks = []
    current = []
    current_tokens = 0

    for block in blocks:
        tokens = len(enc.encode(block))

        if current_tokens + tokens > max_tokens:
            chunk = "\n\n".join(current)
            chunks.append(chunk)

            overlap_text = chunk[-overlap * 4 :]
            current = [overlap_text, block]
            current_tokens = len(enc.encode(overlap_text)) + tokens
        else:
            current.append(block)
            current_tokens += tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


async def embed_chunks(user, chunks: list[str], batch_size=32) -> list[list[float]]:
    user = await openrouter.add_openrouter_to_user(user)
    model = await openrouter.get_ai_model(EMBED_MODEL)
    usd_rate = await get_usd_rate()

    embeddings: list[list[float]] = []

    os.environ["ALL_PROXY"] = config.openrouter.proxy
    async with openrouter.OpenRouter(api_key=user.or_api_key) as app:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            tokens_estimate = sum(len(enc.encode(c)) for c in batch)
            await openrouter.check_balance_before_request(
                user, model, tokens_estimate, usd_rate
            )

            response = await app.embeddings.generate_async(
                model=model.id,
                input=batch,
                encoding_format="float",
            )

            if not response or not response.data:
                raise openrouter.OpenRouterResponseError("Пустой ответ от embeddings")

            await openrouter.charge_user_for_usage(
                user, model, response.usage, usd_rate
            )

            embeddings.extend([e.embedding for e in response.data])

    os.environ.pop("ALL_PROXY", None)

    return embeddings


async def save_chunks(
    *,
    project_id: int,
    document_id: int,
    chunks: Sequence[str],
    embeddings: Sequence[list[float]],
    batch_size: int = 200,
):
    assert len(chunks) == len(embeddings)

    conn = Tortoise.get_connection("default")

    sql_template = """
        INSERT INTO knowledge_chunks
            (project_id, document_id, content, embedding, metadata)
        VALUES
            {values}
    """

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        batch_embeddings = embeddings[i : i + batch_size]

        values_sql = []
        params = []

        for text, embedding in zip(batch_chunks, batch_embeddings):
            values_sql.append("(%s, %s, %s, %s::vector, %s)")
            params.extend(
                [
                    project_id,
                    document_id,
                    text,
                    embedding,  # list[float]
                    None,  # metadata
                ]
            )

        sql = sql_template.format(values=", ".join(values_sql))

        await conn.execute_insert(sql, params)


@hatchet.task(
    name="save_documents",
    input_validator=ProjectDocumentsIn,
    execution_timeout=timedelta(minutes=20),
    schedule_timeout=timedelta(minutes=20),
)
async def save_documents(data: ProjectDocumentsIn, ctx: Context):
    await asyncio.sleep(2)
    logger = StreamLogger(ctx)

    project = await orm.Project.get(id=data.project_id)
    user = await orm.User.get(id=project.user_id)
    documents = await fetch_all(data.documents)

    await logger.info("Начата загрузка документов")

    for document in documents:
        params = document.model_dump()
        content = params.pop("content")

        chunks = chunk_text(content)

        params.update(
            project_id=data.project_id,
            text_length=len(content),
            chunks_count=len(chunks),
        )

        orm_document = await orm.ProjectDocument.create(**params)

        await logger.info(f"Документ {orm_document.filename}: {len(chunks)} чанков")
        try:
            embeddings = await embed_chunks(user, chunks)
        except Exception as e:
            await logger.error(e)
            await orm_document.delete()
            continue

        await save_chunks(
            project_id=data.project_id,
            document_id=orm_document.id,
            chunks=chunks,
            embeddings=embeddings,
        )

    await logger.info("Загрузка документов завершена")
