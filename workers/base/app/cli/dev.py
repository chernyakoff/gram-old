from cyclopts import App
from rich import print

from app.config import config
from app.tasks.heartbeat.task import heartbeat

app = App(name="dev", help="dev tests etc")


@app.command
async def test():
    heartbeat()
