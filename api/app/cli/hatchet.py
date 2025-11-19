from cyclopts import App
from rich import print

from app.config import config
from app.hatchet.client import hatchet

app = App(name="hatchet", help="hatched")


@app.command
async def list():
    # Получаем список всех тасков
    tasks = await hatchet.runs.aio_list()  # можно добавить фильтры
    print(tasks)
