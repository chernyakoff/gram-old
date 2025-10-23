import hashlib
import hmac

from cyclopts import App
from rich import print

from app.common.models.orm import Project
from app.common.utils.prompt import build_prompt
from app.config import config

app = App(name="dev", help="dev tests etc")


@app.command
async def qwerty():
    project = await Project.get(id=6)
    prompt = await build_prompt(project.prompt)

    print(prompt)
