from typing import AsyncGenerator

from pydantic import BaseModel, ConfigDict
from tortoise import BaseDBAsyncClient

from config import get_worker_config, init_db, shutdown_db
from workers.dialog.client import hatchet
from workers.dialog.task.task import dialog_task


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

worker_config = get_worker_config("dialog")

worker = hatchet.worker(
    name=worker_config.name,
    slots=worker_config.slots,
    durable_slots=worker_config.slots,
    workflows=[dialog_task],
    lifespan=lifespan,
)
