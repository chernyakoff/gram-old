from cyclopts import App
from html_to_markdown import convert
from rich import print

from app.common.models.orm import Brief, Project, Prompt, User
from app.common.utils.functions import pick

app = App(name="dev", help="dev tests etc")


@app.command
async def migrate():
    required_keys = [
        "role",
        "context",
        "init",
        "engage",
        "offer",
        "closing",
        "instruction",
        "rules",
        "transitions",
    ]
    projects = await Project.filter().all()
    for p in projects:
        if p.old_prompt:
            prompt = pick(required_keys, p.old_prompt)
            for k, v in prompt.items():
                prompt[k] = convert(v)
            prompt["project_id"] = p.id
            await Prompt.create(**prompt)

        brief_exists = await Brief.get_or_none(project_id=p.id)
        if not brief_exists:
            await Brief.create(
                project_id=p.id,
                description="",
                offer="",
                client="",
                pains="",
                advantages="",
                mission="",
                focus="",
            )
