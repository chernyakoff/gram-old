import asyncio

from hatchet_sdk import Context
from pydantic import BaseModel

from app.client import hatchet
from app.common.utils.s3 import AsyncS3Client
from app.utils.stream_logger import StreamLogger

from .model import Proxy


class ProxiesUploadIn(BaseModel):
    user_id: int
    s3path: str


@hatchet.task(name="proxies-upload", input_validator=ProxiesUploadIn)
async def proxies_upload(input: ProxiesUploadIn, ctx: Context):
    await asyncio.sleep(2)

    async with AsyncS3Client() as s3:
        content_bytes = await s3.get(input.s3path)

    content = content_bytes.decode("utf-8")
    proxies = content.strip().splitlines()

    semaphore = asyncio.Semaphore(10)
    logger = StreamLogger(ctx)

    await logger.info(f"Найдено {len(proxies)} прокси")

    async def save(line: str, logger: StreamLogger):
        try:
            proxy = Proxy.from_line(line)
            ip = await proxy.check()
            if not ip:
                raise ValueError("Ошибка подключения")
            country = await proxy.get_country(ip)
            if not country:
                raise ValueError("Не определяется страна")
            orm_proxy = proxy.to_orm(user_id=input.user_id, country=country)
            try:
                await orm_proxy.save()
            except:
                raise ValueError("Уже загружено")

            await logger.success(line)

        except Exception as e:
            await logger.error(f"{line} {e}")

    async def wrapper(line: str):
        async with semaphore:
            await save(line, logger)

    await asyncio.gather(*(wrapper(p) for p in proxies))

    async with AsyncS3Client() as s3:
        await s3.delete(input.s3path)
