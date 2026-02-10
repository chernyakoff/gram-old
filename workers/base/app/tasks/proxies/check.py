import asyncio
from datetime import timedelta

from hatchet_sdk import Context
from pydantic import BaseModel
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.proxy import ProxyUtil
from app.utils.stream_logger import StreamLogger


class ProxiesCheckIn(BaseModel):
    ids: list[int]


async def _check(proxy: orm.Proxy, logger: StreamLogger):
    util = ProxyUtil.from_orm(proxy)
    if await util.check(max_retries=3):
        await logger.success(util.line)
        async with in_transaction() as conn:
            proxy.failures = 0
            proxy.active = True
            await proxy.save(
                update_fields=["failures", "active", "updated_at"], using_db=conn
            )
    else:
        async with in_transaction() as conn:
            proxy.failures = 5
            proxy.active = False
            await proxy.save(
                update_fields=["failures", "active", "updated_at"], using_db=conn
            )
        await logger.error(util.line)


@hatchet.task(
    name="proxies-check",
    input_validator=ProxiesCheckIn,
    execution_timeout=timedelta(minutes=60),
    schedule_timeout=timedelta(minutes=60),
)
async def proxies_check(input: ProxiesCheckIn, ctx: Context):
    await asyncio.sleep(2)  # эмуляция задержки
    logger = StreamLogger(ctx)
    proxies = await orm.Proxy.filter(id__in=input.ids).all()
    tasks = [_check(proxy, logger) for proxy in proxies]
    await asyncio.gather(*tasks)
