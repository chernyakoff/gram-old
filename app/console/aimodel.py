from utils import openrouter
from utils.cyclopts import create_app

app = create_app(
    "aimodel",
    "Обновление списка моделей openrouter. опирается на существующие модели в базе",
)


@app.command
async def upsert_models():
    await openrouter.upsert_models()  # type: ignore
