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

from config import config
from models import orm
from utils import openrouter
from utils.s3 import AsyncS3Client
from utils.usd_rate import get_usd_rate
from workers.base.client import hatchet
from utils.logger import StreamLogger

_enc = None


def get_encoder():
    # Lazy init: prevents network/download during module import (important for stub codegen).
    global _enc
    if _enc is None:
        _enc = tiktoken.get_encoding("cl100k_base")
    return _enc


HEADER_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)
HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
LONG_UNDERSCORE_RE = re.compile(r"^\s*_{8,}\s*$", re.MULTILINE)
NUMBERED_ITEM_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)(?P<num>\d{1,4})(?P<delim>[.)])[ \t]+"
)
BULLET_ITEM_RE = re.compile(r"(?m)^(?P<indent>[ \t]*)(?:[-*+])[ \t]+")

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
    if any(NUMBERED_ITEM_RE.match(line) for line in lines):
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
    # Common "visual separators" frequently seen in exported docs.
    # Remove them so they don't pollute chunks and so list/header splitting works better.
    text = LONG_UNDERSCORE_RE.sub("", text)
    text = HR_RE.sub("", text)
    return text.strip()


def _split_by_list_items(
    text: str,
    *,
    item_re: re.Pattern[str],
    max_items_per_chunk: int,
    min_tokens: int,
    max_tokens: int,
    tiktoken_len,
) -> list[str]:
    """
    Split long lists (numbered/bulleted) into reasonable blocks.

    Motivation: exported docs often contain 10+ list items without headings; a header-only splitter
    will keep that as one chunk, hurting retrieval quality.
    """
    starts = [m.start() for m in item_re.finditer(text)]
    if len(starts) < 2:
        t = text.strip()
        return [t] if t else []

    blocks: list[str] = []
    preface = text[: starts[0]].strip()
    if preface:
        blocks.append(preface)

    items: list[str] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        item = text[s:e].strip()
        if item:
            items.append(item)

    packed: list[str] = []
    cur_parts: list[str] = []
    cur_tokens = 0
    cur_items = 0

    def flush():
        nonlocal cur_parts, cur_tokens, cur_items
        if cur_parts:
            packed.append("\n\n".join(cur_parts).strip())
        cur_parts = []
        cur_tokens = 0
        cur_items = 0

    for item in items:
        item_tokens = tiktoken_len(item)
        if item_tokens > max_tokens:
            # Keep the oversized item standalone; it will be split in a later pass.
            flush()
            packed.append(item)
            continue

        next_tokens = cur_tokens + (2 if cur_parts else 0) + item_tokens
        should_flush = (
            (cur_parts and next_tokens > max_tokens)
            or (cur_items >= max_items_per_chunk)
            or (cur_parts and cur_tokens >= min_tokens)
        )
        if should_flush:
            flush()

        cur_parts.append(item)
        cur_tokens = cur_tokens + (2 if len(cur_parts) > 1 else 0) + item_tokens
        cur_items += 1

    flush()
    blocks.extend([b for b in packed if b])
    return blocks

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
        return len(get_encoder().encode(s))

    # Token-aware recursive splitter used as a final fallback for any block.
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=overlap,
        length_function=tiktoken_len,
        separators=[
            "\n\n",
            "\n",
            ". ",
            "! ",
            "? ",
            "; ",
            ": ",
            ", ",
            " ",
            "",
        ],
    )

    blocks: list[str] = []

    if text_type == "markdown":
        header_splitter = MarkdownHeaderTextSplitter(
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
        header_docs = header_splitter.split_text(text)
        header_blocks: list[str] = []
        for d in header_docs:
            if isinstance(d, Document):
                b = d.page_content.strip()
            else:
                b = str(d).strip()
            if b:
                header_blocks.append(b)

        for b in header_blocks or [text]:
            list_blocks = _split_by_list_items(
                b,
                item_re=NUMBERED_ITEM_RE,
                max_items_per_chunk=4,
                min_tokens=min_tokens,
                max_tokens=max_tokens,
                tiktoken_len=tiktoken_len,
            )
            if len(list_blocks) == 1:
                list_blocks = _split_by_list_items(
                    b,
                    item_re=BULLET_ITEM_RE,
                    max_items_per_chunk=6,
                    min_tokens=min_tokens,
                    max_tokens=max_tokens,
                    tiktoken_len=tiktoken_len,
                )
            blocks.extend(list_blocks)
    else:
        blocks = _split_by_list_items(
            text,
            item_re=NUMBERED_ITEM_RE,
            max_items_per_chunk=4,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            tiktoken_len=tiktoken_len,
        )
        if len(blocks) == 1:
            blocks = _split_by_list_items(
                text,
                item_re=BULLET_ITEM_RE,
                max_items_per_chunk=6,
                min_tokens=min_tokens,
                max_tokens=max_tokens,
                tiktoken_len=tiktoken_len,
            )

    # Final pass: make sure every block respects max_tokens via token-aware recursive splitting.
    raw_chunks: list[str] = []
    for b in blocks:
        if tiktoken_len(b) <= max_tokens:
            raw_chunks.append(b)
        else:
            raw_chunks.extend(recursive_splitter.split_text(b))

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

            tokens_estimate = sum(len(get_encoder().encode(c)) for c in batch)
            await openrouter.check_balance_before_request(
                user, model, tokens_estimate, usd_rate
            )

            response = await app.embeddings.generate_async(
                model=model.id,
                input=batch,
                encoding_format="float",
            )

            if not response or not response.data:  # type: ignore
                raise openrouter.OpenRouterResponseError("Пустой ответ от embeddings")

            await openrouter.charge_user_for_embedding_usage(
                user,
                model,
                response.usage,  # type: ignore
                usd_rate,
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
