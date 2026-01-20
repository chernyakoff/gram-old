import asyncio
import os
import re
from datetime import timedelta
from typing import Sequence

import tiktoken
from hatchet_sdk import Context
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
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


def detect_text_type(text: str) -> str:
    """
    Определяем тип текста для выбора сплиттера.
    Если текст содержит заголовки, списки или блоки кода — Markdown.
    """
    lines = text.splitlines()
    if any(line.startswith(("#", "-", "*", ">")) for line in lines):
        return "markdown"
    if "```" in text:
        return "markdown"
    return "plain"


def normalize(text: str) -> str:
    """
    Чистим текст от лишних переносов, разделителей, обрезаем пробелы.
    """
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*(---|\*\*\*)\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def chunk_text(
    text: str,
    min_tokens: int = 200,
    max_tokens: int = 700,
    overlap: int = 120,
) -> list[str]:
    """
    Разбиваем текст на чанки для embedding.
    Используется LangChain сплиттер + tiktoken для точного подсчета токенов.
    Автоматически выбирается Markdown-aware сплиттер.
    """
    text = normalize(text)
    text_type = detect_text_type(text)

    # Функция подсчета токенов через tiktoken
    def tiktoken_len(s: str) -> int:
        return len(enc.encode(s))

    # Выбираем сплиттер
    if text_type == "markdown":
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
                ("####", "h4"),
                ("#####", "h5"),
                ("######", "h6"),
            ],
            strip_headers=True,
            return_each_line=False,
        )
    else:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=overlap,
            length_function=tiktoken_len,
        )

    raw_chunks = splitter.split_text(text)
    chunks: list[str] = []

    for c in raw_chunks:
        if isinstance(c, Document):
            chunks.append(c.page_content.strip())
        else:
            chunks.append(c.strip())

    chunks = [
        c for c in chunks if len(c) > 30 and not re.match(r"^[^A-Za-zА-Яа-я0-9#]+", c)
    ]

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

            await openrouter.charge_user_for_embedding_usage(
                user, model, response.usage, usd_rate
            )

            embeddings.extend([e.embedding for e in response.data])  # type: ignore

    os.environ.pop("ALL_PROXY", None)

    return embeddings


def embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


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

        values_sql: list[str] = []
        params: list[object] = []
        param_idx = 1

        for text, embedding in zip(batch_chunks, batch_embeddings):
            values_sql.append(
                f"(${param_idx}, ${param_idx + 1}, ${param_idx + 2}, ${param_idx + 3}::vector, ${param_idx + 4})"
            )

            params.extend(
                [
                    project_id,
                    document_id,
                    text,
                    embedding_to_pgvector(embedding),  # ✅ STRING
                    None,
                ]
            )

            param_idx += 5

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
