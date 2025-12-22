import httpx
from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.common.models import orm
from app.common.models.enums import DialogStatus
from app.common.utils.prompt import ProjectSkipOptions, build_prompt_v2
from app.common.utils.usd_rate import get_usd_rate
from app.dto.project import ProjectOut

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    project = await orm.Project.get(id=177)
    status = DialogStatus.ENGAGE

    orm_prompt = await orm.Prompt.get(project_id=project.id)

    skip_options = ProjectSkipOptions(engage=True, offer=True, closing=False)

    # prompt = build_prompt(orm_prompt.to_dict(), chat.status)
    prompt = build_prompt_v2(orm_prompt.to_dict(), status, skip_options)
    # print(prompt)
