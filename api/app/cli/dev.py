from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import List

from cyclopts import App
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models.enums import WeekDay
from app.common.models.orm import Dialog, Meeting, User
from app.common.utils.openrouter import create_response_with_tools
from app.common.utils.schedule import TOOLS, ToolContext

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    user = await User.get(id=359107176)
    dialog = await Dialog.get(id=2367)
    ctx = ToolContext(user, dialog)
    tool_handlers = {
        "get_slots": ctx.get_slots,
        "book_slot": ctx.book_slot,
    }
    history = []
    text = await create_response_with_tools(
        user=user,
        history=history,
        tools=TOOLS,
        tool_handlers=tool_handlers,
    )
