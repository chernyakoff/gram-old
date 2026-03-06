import asyncio
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import Sequence

from hatchet_sdk import Context
from markitdown import MarkItDown
from pydantic import BaseModel
from tortoise import Tortoise

from models import orm
from utils import openrouter
from utils.logger import StreamLogger
from utils.s3 import AsyncS3Client
from workers.base.client import hatchet


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
    content: bytes


class ProjectDocumentsIn(BaseModel):
    project_id: int
    documents: list[ProjectDocument]


async def fetch_file(document: ProjectDocument) -> ProjectDocumentFull:
    async with AsyncS3Client() as s3:  # type: ignore
        content_bytes = await s3.get(document.storage_path)

    params = document.model_dump()
    params["content"] = content_bytes
    return ProjectDocumentFull(**params)


async def fetch_all(documents: list[ProjectDocument]) -> list[ProjectDocumentFull]:
    tasks = [fetch_file(d) for d in documents]
    return await asyncio.gather(*tasks)


def _resolve_extension(filename: str, content_type: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "docx":
        return "docx"

    ctype = content_type.lower()
    if "wordprocessingml" in ctype or "docx" in ctype:
        return "docx"
    return ""


def _convert_doc_to_markdown_sync(document: ProjectDocumentFull) -> str:
    extension = _resolve_extension(document.filename, document.content_type)
    if extension != "docx":
        raise ValueError(
            f"unsupported document type (docx only): filename={document.filename}, content_type={document.content_type}"
        )

    converter = MarkItDown(enable_plugins=False)
    stream = BytesIO(document.content)
    stream.name = document.filename
    result = converter.convert_stream(stream, file_extension="docx")

    markdown = (result.text_content or "").strip()
    if not markdown:
        raise ValueError("empty markdown after conversion")

    return markdown


async def convert_doc_to_markdown(
    document: ProjectDocumentFull, logger: StreamLogger
) -> str:
    try:
        return await asyncio.to_thread(_convert_doc_to_markdown_sync, document)
    except Exception as e:
        await logger.error(f"Не удалось конвертировать документ {document.filename}")
        await logger.tech(
            "save_documents convert failed",
            payload={
                "filename": document.filename,
                "storage_path": document.storage_path,
                "content_type": document.content_type,
            },
            exc=e,
        )
        raise


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
                    embedding_to_pgvector(embedding),
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

    await logger.info("Начата загрузка документов")

    try:
        documents = await fetch_all(data.documents)
    except Exception as e:
        await logger.error("Не удалось загрузить документы из хранилища")
        await logger.tech(
            "save_documents fetch failed",
            payload={"project_id": data.project_id, "documents_count": len(data.documents)},
            exc=e,
        )
        return

    for document in documents:
        await logger.info(f"Обработка документа {document.filename}")

        try:
            markdown = await convert_doc_to_markdown(document, logger)
        except Exception:
            continue

        chunks = openrouter.chunk_markdown(markdown)
        if not chunks:
            await logger.warning(f"Документ {document.filename} не содержит текста для чанков")
            await logger.tech(
                "save_documents empty chunks",
                payload={
                    "project_id": data.project_id,
                    "filename": document.filename,
                    "storage_path": document.storage_path,
                },
            )
            continue

        orm_document = await orm.ProjectDocument.create(
            filename=document.filename,
            file_size=document.file_size,
            storage_path=document.storage_path,
            content_type=document.content_type,
            project_id=data.project_id,
            text_length=len(markdown),
            chunks_count=len(chunks),
        )

        await logger.info(f"Документ {orm_document.filename}: {len(chunks)} чанков")

        try:
            embeddings = await openrouter.embed_chunks(user, chunks)
        except Exception as e:
            await logger.error(f"Ошибка embeddings для {document.filename}")
            await logger.tech(
                "save_documents embeddings failed",
                payload={
                    "project_id": data.project_id,
                    "document_id": orm_document.id,
                    "filename": document.filename,
                    "chunks_count": len(chunks),
                },
                exc=e,
            )
            await orm_document.delete()
            continue

        try:
            await save_chunks(
                project_id=data.project_id,
                document_id=orm_document.id,
                chunks=chunks,
                embeddings=embeddings,
            )
        except Exception as e:
            await logger.error(f"Ошибка сохранения чанков для {document.filename}")
            await logger.tech(
                "save_documents persist chunks failed",
                payload={
                    "project_id": data.project_id,
                    "document_id": orm_document.id,
                    "filename": document.filename,
                    "chunks_count": len(chunks),
                },
                exc=e,
            )
            await orm_document.delete()
            continue

        await logger.success(f"Документ {document.filename} обработан")

    await logger.success("Загрузка документов завершена")
