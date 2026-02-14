from typing import AsyncGenerator

from pydantic import BaseModel, ConfigDict
from tortoise import BaseDBAsyncClient

from config import get_worker_config, init_db, shutdown_db
from workers.base.client import hatchet
from workers.base.accounts.check import accounts_check
from workers.base.accounts.premium import buy_premium
from workers.base.accounts.stop_premium import stop_premium
from workers.base.accounts.update import accounts_update
from workers.base.accounts.upload import accounts_upload
from workers.base.documents.task import save_documents
from workers.base.heartbeat.task import heartbeat
from workers.base.nightly.task import nightly
from workers.base.prompt.task import generate_prompt
from workers.base.proxies.check import proxies_check
from workers.base.proxies.upload import proxies_upload
from workers.base.synonimize.task import synonimize


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

worker_config = get_worker_config("base")

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
        save_documents,
        heartbeat,
        nightly,
    ],
    lifespan=lifespan,
)
