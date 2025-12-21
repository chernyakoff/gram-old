import httpx
from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.common.models import orm
from app.common.utils.usd_rate import get_usd_rate
from app.dto.project import ProjectOut

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    project = await orm.Project.get(id=177)
    project_out = await ProjectOut.from_tortoise_orm(project)
    print(project_out.model_dump())
