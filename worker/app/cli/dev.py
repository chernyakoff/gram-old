from cyclopts import App
from rich import print

from app.config import config

app = App(name="dev", help="dev tests etc")


@app.command
async def test():
    print(config.model_dump())
