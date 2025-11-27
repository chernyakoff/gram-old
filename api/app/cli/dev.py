from cyclopts import App
from html_to_markdown import convert
from rich import print

from app.common.models.orm import Brief, Project, Prompt, User
from app.common.utils.functions import pick

app = App(name="dev", help="dev tests etc")


@app.command
async def migrate():
    pass
