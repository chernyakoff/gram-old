import asyncio

from cyclopts import App
from app.common.utils import vars
from app.config import init_db

app = App(usage="Usage: pdm run cli [COMMAND] [OPTION]")


@app.meta.default
def on_startup(*tokens: str):
    asyncio.run(init_db())
    app(tokens)


for subapp in vars.load("app.cli:app", App):
    app.command(subapp)


if __name__ == "__main__":
    app.meta()
