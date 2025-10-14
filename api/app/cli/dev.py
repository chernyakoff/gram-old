from datetime import datetime

from cyclopts import App
from pydantic import BaseModel, Field
from rich import print
from tortoise.query_utils import Prefetch

from app.common.models import orm
from app.common.utils.s3 import AsyncS3Client
from app.dto import mailing
from app.dto.account import AccountOut
from app.routers.chat import generate_message

app = App(name="dev", help="dev tests etc")


@app.command
async def qwerty():
    hz = await orm.Dialog.filter(
        recipient__mailing__user_id=359107176
    ).prefetch_related("recipient", "recipient__mailing")
    print(hz)
