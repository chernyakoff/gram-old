from typing import AsyncGenerator

from pydantic import BaseModel, ConfigDict
from tortoise import BaseDBAsyncClient

from app.client import hatchet
from app.config import init_db, shutdown_db, worker_config
from app.tasks.accounts.check import accounts_check, accounts_check_mp
from app.tasks.accounts.premium import buy_premium, buy_premium_mp
from app.tasks.accounts.stop_premium import stop_premium, stop_premium_mp
from app.tasks.accounts.update import accounts_update, accounts_update_mp
from app.tasks.accounts.upload import accounts_upload, accounts_upload_mp
from app.tasks.daily.task import daily
from app.tasks.heartbeat.task import heartbeat, mp_heartbeat
from app.tasks.prompt.task import generate_prompt
from app.tasks.proxies.check import proxies_check
from app.tasks.proxies.upload import proxies_upload
from app.tasks.synonimize.task import synonimize


class LifespanContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    db: BaseDBAsyncClient


async def lifespan() -> AsyncGenerator[LifespanContext, None]:
    conn = await init_db()

    ctx = LifespanContext(db=conn)
    print("DB initialized!")
    try:
        yield ctx
    finally:
        print("Cleaning up DB...")
        await shutdown_db()


worker = hatchet.worker(
    name=worker_config.name,
    slots=worker_config.slots,
    workflows=[
        proxies_upload,
        accounts_upload,
        accounts_upload_mp,
        accounts_update,
        accounts_update_mp,
        accounts_check,
        accounts_check_mp,
        proxies_check,
        buy_premium,
        buy_premium_mp,
        generate_prompt,
        synonimize,
        stop_premium,
        stop_premium_mp,
        heartbeat,
        mp_heartbeat,
        daily,
    ],
    lifespan=lifespan,
)
