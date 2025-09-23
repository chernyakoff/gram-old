from typing import AsyncGenerator

from hatchet_sdk import Context, EmptyModel
from pydantic import BaseModel, ConfigDict
from tortoise import BaseDBAsyncClient

from app.accounts.update import accounts_update
from app.accounts.upload import accounts_upload
from app.client import hatchet
from app.config import config, init_db, shutdown_db
from app.proxies.upload import proxies_upload


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
    config.worker.name,
    slots=config.worker.slots,
    workflows=[proxies_upload, accounts_upload, accounts_update],
    lifespan=lifespan,
)
