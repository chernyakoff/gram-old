from typing import AsyncGenerator

from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis
from tortoise import BaseDBAsyncClient

from app.client import hatchet
from app.config import init_db, shutdown_db, worker_config
from app.redis import init_redis, shutdown_redis
from app.tasks.accounts.check import accounts_check
from app.tasks.accounts.premium import buy_premium
from app.tasks.accounts.stop_premium import stop_premium
from app.tasks.accounts.update import accounts_update
from app.tasks.accounts.upload import accounts_upload
from app.tasks.daily.task import daily
from app.tasks.heartbeat.task import heartbeat, mp_heartbeat
from app.tasks.prompt.task import generate_prompt
from app.tasks.proxies.check import proxies_check
from app.tasks.proxies.upload import proxies_upload
from app.tasks.synonimize.task import synonimize


class LifespanContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    db: BaseDBAsyncClient
    redis: Redis


async def lifespan() -> AsyncGenerator[LifespanContext, None]:
    conn = await init_db()
    redis = await init_redis()

    ctx = LifespanContext(db=conn, redis=redis)
    print("DB initialized!")
    try:
        yield ctx
    finally:
        print("Cleaning up DB...")
        await shutdown_redis()
        await shutdown_db()


worker = hatchet.worker(
    name=worker_config.name,
    slots=worker_config.slots,
    workflows=[
        proxies_upload,
        accounts_upload,
        accounts_update,
        accounts_check,
        proxies_check,
        buy_premium,
        generate_prompt,
        synonimize,
        stop_premium,
        heartbeat,
        mp_heartbeat,
        daily,
    ],
    lifespan=lifespan,
)
