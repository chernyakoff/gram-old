import asyncio
from datetime import timedelta

from hatchet_sdk import Context
from pydantic import BaseModel
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models.enums import AccountStatus
from app.common.models.orm import Account
from app.common.utils.proxy import ProxyUtil
from app.utils.stream_logger import StreamLogger


class ProxiesUploadIn(BaseModel):
    user_id: int
    proxies: list[str]


@hatchet.task(
    name="proxies-upload",
    input_validator=ProxiesUploadIn,
    execution_timeout=timedelta(hours=1),
    schedule_timeout=timedelta(hours=1),
)
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
            await orm_proxy.save()
            async with in_transaction() as conn:
                await (
                    Account.filter(
                        user_id=input.user_id,
                        status=AccountStatus.NOPROXY,
                        proxy_id__isnull=True,
                        country=orm_proxy.country,
                    )
                    .using_db(conn)
                    .update(
                        status=AccountStatus.GOOD,
                        proxy_id=orm_proxy.id,
                        active=True,
                    )
                )

            await logger.success(line)

        except IntegrityError:
            await logger.error(f"{line} уже был загружен")
        except Exception as e:
            await logger.error(f"{line} {e}")

    async def wrapper(line: str):
        async with semaphore:
            await save(line, logger)

    await asyncio.gather(*(wrapper(p) for p in input.proxies))
