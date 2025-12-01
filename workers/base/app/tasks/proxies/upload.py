import asyncio

from hatchet_sdk import Context
from pydantic import BaseModel

from app.client import hatchet
from app.common.utils.proxy import ProxyUtil
from app.utils.stream_logger import StreamLogger


class ProxiesUploadIn(BaseModel):
    user_id: int
    proxies: list[str]


@hatchet.task(name="proxies-upload", input_validator=ProxiesUploadIn)
async def proxies_upload(input: ProxiesUploadIn, ctx: Context):
    await asyncio.sleep(2)

    semaphore = asyncio.Semaphore(10)
    logger = StreamLogger(ctx)

    await logger.info(f"Найдено {len(input.proxies)} прокси")

    async def save(line: str, logger: StreamLogger):
        try:
            proxy = ProxyUtil.from_line(line)
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

    await asyncio.gather(*(wrapper(p) for p in input.proxies))
