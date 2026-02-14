from rich import print

from api.hatchet.client import hatchet
from utils.cyclopts import create_app

app = create_app("hatchet", "для экспериментов c hatchet")


@app.command
async def list():
    # Получаем список всех тасков
    tasks = await hatchet.runs.aio_list()  # можно добавить фильтры
    print(tasks)
