import os
from io import StringIO

from cyclopts import App
from rich import print

from app.common.models import orm
from app.common.models.enums import DialogStatus, MessageSender
from app.common.utils.notify import send_file_to_user
from app.common.utils.prompt import build_prompt

app = App(name="prompt")

CHAT_ID = 359107176


@app.default
async def _(id: str):
    if id.isdigit():
        user = await orm.User.get_or_none(id=id)
    else:
        user = await orm.User.get_or_none(username=id.removeprefix("@"))
    if not user:
        print("Пользователь не найден")
        return
    result = []

    prompts = await orm.Prompt.filter(project__user_id=user.id).all()
    for prompt in prompts:
        result.append(build_prompt(prompt.to_dict()))

    buf = StringIO()
    buf.write("\n\n\n".join(result))
    file_bytes = buf.getvalue().encode("utf-8")

    await send_file_to_user(
        CHAT_ID, f"prompt_{user.username}.txt", file_bytes, f"Промпт {user.username}"
    )
