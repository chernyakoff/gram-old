# app/router/projects.py

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.common.models import orm
from app.common.utils.prompt import DEFAULT_SKIP_OPTIONS, ProjectSkipOptions
from app.dto.common import WorkflowOut
from app.dto.project import (
    ProjectBase,
    ProjectFilesIn,
    ProjectShortOut,
    ProjectStatusIn,
    SynonimizeIn,
)
from app.hatchet.base import models, tasks
from app.routers.auth import get_current_user
from app.routers.sse import watch_job

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectShortOut])
async def get_projects(user=Depends(get_current_user)):
    return await ProjectShortOut.from_queryset(orm.Project.filter(user_id=user.id))


@router.get("/list", response_model=list[ProjectBase])
async def get_project_list(user=Depends(get_current_user)):
    return await ProjectBase.from_queryset(orm.Project.filter(user_id=user.id))


@router.delete("/")
async def delete_projects(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Project.filter(id__in=id, user_id=user.id).delete()


@router.patch("/{id}/status")
async def update_project_status(
    id: int, data: ProjectStatusIn, user=Depends(get_current_user)
):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    project.status = data.status
    await project.save()


@router.post("/synonimize", response_model=models.SynonimizeOut)
async def synonimize(data: SynonimizeIn, user=Depends(get_current_user)):
    response = await tasks.synonimize.aio_run(
        models.SynonimizeIn(text=data.text, user_id=user.id)
    )
    return response


@router.post("/upload-files", response_model=WorkflowOut)
async def upload_files(data: ProjectFilesIn, user=Depends(get_current_user)):
    print(data)


# рефакторинг ----------------------------------------

# создание проекта


class ProjectCreateIn(BaseModel):
    name: str


@router.post("/create")
async def create_project(data: ProjectCreateIn, user=Depends(get_current_user)):
    await orm.Project.create(
        name=data.name, user_id=user.id, active=False, skip_options=DEFAULT_SKIP_OPTIONS
    )


# настройки проекта


class ProjectSettings(BaseModel):
    name: str
    dialog_limit: int
    send_time_start: int
    send_time_end: int
    first_message: str
    premium_required: bool


@router.get("/{id}/settings", response_model=ProjectSettings)
async def get_project_settings(id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    if not project.first_message:
        project.first_message = ""
    return ProjectSettings(
        name=project.name,
        dialog_limit=project.dialog_limit,
        send_time_start=project.send_time_start,
        send_time_end=project.send_time_end,
        first_message=project.first_message,
        premium_required=project.premium_required,
    )


@router.post("/{id}/settings")
async def update_project_settings(
    id: int, data: ProjectSettings, user=Depends(get_current_user)
):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    project.update_from_dict(data.model_dump())
    await project.save()


# бриф


class Brief(BaseModel):
    description: str
    offer: str
    client: str
    pains: str
    advantages: str
    mission: str
    focus: str


@router.get("/{id}/brief", response_model=Brief)
async def get_brief(id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    brief = await orm.Brief.get_or_none(project_id=id)
    if not brief:
        brief = await orm.Brief.create(
            project_id=id,
            description="",
            offer="",
            client="",
            pains="",
            advantages="",
            mission="",
            focus="",
        )

    return Brief(
        description=brief.description,
        offer=brief.offer,
        client=brief.client,
        pains=brief.pains,
        advantages=brief.advantages,
        mission=brief.mission,
        focus=brief.focus,
    )


@router.post("/{id}/brief")
async def save_brief(id: int, data: Brief, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    brief = await orm.Brief.get(project_id=id)
    brief.update_from_dict(data.model_dump())
    await brief.save()


@router.post("/{id}/generate-prompt", response_model=WorkflowOut)
async def generate_prompt(id: int, data: Brief, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    brief = await orm.Brief.get(project_id=id)
    brief.update_from_dict(data.model_dump())
    await brief.save()
    ref = await tasks.generate_prompt.aio_run_no_wait(
        input=models.GeneratePromptIn(project_id=project.id)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore

    return {"id": ref.workflow_run_id}


# промпт


class Prompt(BaseModel):
    role: str
    context: str
    init: str
    engage: str
    offer: str
    closing: str
    instruction: str
    rules: str
    skip_options: ProjectSkipOptions


@router.get("/{id}/prompt", response_model=Prompt)
async def get_prompt(id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    prompt = await orm.Prompt.get_or_none(project_id=id)
    if not prompt:
        prompt = await orm.Prompt.create(
            project_id=id,
            role="",
            context="",
            init="",
            engage="",
            offer="",
            closing="",
            instruction="",
            rules="",
        )

    skip_options = (
        ProjectSkipOptions(**project.skip_options)
        if project.skip_options
        else DEFAULT_SKIP_OPTIONS
    )
    return Prompt(
        role=prompt.role,
        context=prompt.context,
        init=prompt.init,
        engage=prompt.engage,
        offer=prompt.offer,
        closing=prompt.closing,
        instruction=prompt.instruction,
        rules=prompt.rules,
        skip_options=skip_options,
    )


@router.post("/{id}/prompt")
async def save_promptf(id: int, data: Prompt, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    params = data.model_dump()
    project.skip_options = params["skip_options"]
    await project.save(update_fields=["skip_options"])
    del params["skip_options"]
    prompt = await orm.Prompt.get(project_id=id)

    prompt.update_from_dict(params)
    await prompt.save()
