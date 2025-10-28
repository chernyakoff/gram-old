import json

from cyclopts import App
from rich import print

from app.common.models.orm import AppSettings, Project

app = App(name="prompt")


@app.command
async def copy_from(project_id: int):
    project = await Project.get(id=project_id)
    await AppSettings.filter(section="prompt").delete()

    await AppSettings.create(
        section="prompt",
        name="first_message",
        value=project.first_message,
    )
    await AppSettings.create(
        section="prompt",
        name="json",
        value=json.dumps(project.prompt, ensure_ascii=False),
    )

    print("готово")
