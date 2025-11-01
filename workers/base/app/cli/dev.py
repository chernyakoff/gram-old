from datetime import timedelta

from cyclopts import App
from hatchet_sdk import Context, EmptyModel
from pydantic import BaseModel
from rich import print
from tortoise import timezone as tz
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm

LEASE_HOURS = 6  # сколько "занятый" аккаунт считается занятым
MAX_ACCOUNTS_PER_CYCLE = 50  # сколько аккаунтов проверяем за 1 тик
RECIPIENT_LEASE_MINUTES = 30  # время аренды recipient перед отправкой в таск


app = App(name="dev", help="dev tests etc")


@app.command
async def test():
    pass
