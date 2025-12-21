from cyclopts import App

from app.common.utils import openrouter

app = App(name="aimodel", help="Generate OpenApi spec")


@app.command
async def upsert_models():
    await openrouter.upsert_models()  # type: ignore
