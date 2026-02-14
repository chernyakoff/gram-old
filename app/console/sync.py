from utils.cyclopts import create_app
from utils.sync import run

app = create_app("sync", "Генерация тасков и моделей для api")


@app.default
def _():
    run()
