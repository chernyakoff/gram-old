from enum import StrEnum
from itertools import product

import httpx
from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.common.models import orm
from app.common.utils.openrouter import upsert_models

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    await upsert_models()
