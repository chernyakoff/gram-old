import asyncio
import re
from datetime import timedelta
from typing import Optional

import tiktoken
from hatchet_sdk import Context
from pydantic import BaseModel

from app.client import hatchet
from app.common.models import orm
from app.common.models.orm import AppSettings, User
from app.common.utils import openrouter
from app.common.utils.s3 import AsyncS3Client
from app.utils.stream_logger import StreamLogger

enc = tiktoken.get_encoding("cl100k_base")

HEADER_RE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)


class ProjectFilesIn(BaseModel):
    project_id: int
    files: list[str]


async def fetch_file(file_id):
    async with AsyncS3Client() as s3:  # type: ignore
        content_bytes = await s3.get(file_id)
        return content_bytes.decode("utf-8")  # предполагаем, что UTF-8 текст


async def fetch_all(files: list[str]):
    tasks = [fetch_file(f) for f in files]
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


async def to_pgvector(s3path: str):
    pass


@hatchet.task(
    name="pgvector",
    input_validator=ProjectFilesIn,
    execution_timeout=timedelta(minutes=20),
    schedule_timeout=timedelta(minutes=20),
)
async def synonimize(data: ProjectFilesIn, ctx: Context):
    await asyncio.sleep(2)
    logger = StreamLogger(ctx)

    project = await orm.Project.get(id=data.project_id)

    documents = await fetch_all(data.files)
