from typing import AsyncGenerator

from pydantic import BaseModel, ConfigDict
from tortoise import BaseDBAsyncClient

from app.client import hatchet
from app.config import init_db, shutdown_db, worker_config
from app.tasks.accounts.update import accounts_update
from app.tasks.accounts.upload import accounts_upload
from app.tasks.heartbeat.task import heartbeat
from app.tasks.proxies.upload import proxies_upload


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
    workflows=[proxies_upload, accounts_upload, accounts_update, heartbeat],
    lifespan=lifespan,
)
