
from cyclopts import App

from app.common.utils.openrouter import upsert_models

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    await upsert_models()
