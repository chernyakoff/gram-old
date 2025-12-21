from hatchet_sdk import Context, EmptyModel

from app.client import hatchet
from app.common.utils import openrouter

daily = hatchet.workflow(name="daily", on_crons=["59 23 * * *"])


@daily.task()
async def task(input: EmptyModel, ctx: Context):
    await openrouter.upsert_models()
