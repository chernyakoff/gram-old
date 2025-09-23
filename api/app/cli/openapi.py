import yaml
from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.app import app as api

app = App(name="openapi", help="Generate OpenApi spec")


@app.default
async def openapi():
    filename = "openapi.yaml"
    spec = yaml.dump(api.openapi(), sort_keys=False, allow_unicode=True)
    await AsyncPath(filename).write_text(spec)
    print(f"{filename} создан")
