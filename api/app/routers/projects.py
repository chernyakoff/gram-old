# app/router/projects.py

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from app.common.models import orm
from app.dto.common import WorkflowOut
from app.dto.project import (
    ProjectBase,
    ProjectIn,
    ProjectOut,
    ProjectShortOut,
    ProjectStatusIn,
    create_default_project,
)
from app.hatchet.base import models, tasks
from app.routers.auth import get_current_user
from app.routers.sse import watch_job

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=WorkflowOut)
async def create_project(data: ProjectIn, user=Depends(get_current_user)):
    # Создаём проект
    project = orm.Project(
        name=data.name,
        dialog_limit=data.dialog_limit,
        send_time_start=data.send_time_start,
        send_time_end=data.send_time_end,
        first_message=data.first_message,
        user_id=user.id,
    )
    await project.save()
    if data.advanced_mode:
        prompt_params = data.prompt.model_dump()
        prompt_params["project_id"] = project.id
        await orm.Prompt.create(**prompt_params)
        return {"id": "NONE"}
    else:
        brief_params = data.brief.model_dump()
        brief_params["project_id"] = project.id
        await orm.Brief.create(**brief_params)
        ref = await tasks.generate_prompt.aio_run_no_wait(
            input=models.GeneratePromptIn(project_id=project.id)
        )
        asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore
        return {"id": ref.workflow_run_id}


@router.get("/", response_model=list[ProjectShortOut])
async def get_projects(user=Depends(get_current_user)):
    return await ProjectShortOut.from_queryset(orm.Project.filter(user_id=user.id))


@router.get("/default", response_model=ProjectIn)
async def get_default_project(user=Depends(get_current_user)):
    return await create_default_project()


@router.get("/list", response_model=list[ProjectBase])
async def get_project_list(user=Depends(get_current_user)):
    qs = orm.Project.filter(user_id=user.id).prefetch_related("prompt")
    return await ProjectBase.from_queryset(qs)


@router.get("/{id}", response_model=ProjectOut)
async def get_project(id: int, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=id, user_id=user.id).prefetch_related(
        "brief"
    )
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    # Используем tortoise-serializer для сериализации с вложенным brief
    return await ProjectOut.from_tortoise_orm(project)


@router.delete("/")
async def delete_projects(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Project.filter(id__in=id, user_id=user.id).delete()


@router.patch("/{id}")
async def update_project(id: int, data: ProjectIn, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)

    if not project:
        raise HTTPException(status_code=404, detail="not found")

    # обновляем проект
    project.name = data.name
    project.dialog_limit = data.dialog_limit
    project.send_time_start = data.send_time_start
    project.send_time_end = data.send_time_end
    project.first_message = data.first_message
    await project.save()

    # режим prompt
    if data.advanced_mode:
        await orm.Prompt.update_or_create(
            project_id=id, defaults=data.prompt.model_dump()
        )
        return {"id": "NONE"}

    brief = await orm.Brief.get_or_none(project_id=project.id)
    incoming = data.brief.model_dump()

    if not brief:
        await orm.Brief.create(project_id=project.id, **incoming)
        brief_changed = True
    else:
        brief_changed = incoming != brief.to_dict()
        if brief_changed:
            for key, value in incoming.items():
                setattr(brief, key, value)
            await brief.save()

    # если ничего не изменилось — выходим
    if not brief_changed:
        return {"id": "NONE"}

    # запускаем генерацию
    ref = await tasks.generate_prompt.aio_run_no_wait(
        input=models.GeneratePromptIn(project_id=project.id)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore

    return {"id": ref.workflow_run_id}


@router.patch("/{id}/status")
async def update_project_status(
    id: int, data: ProjectStatusIn, user=Depends(get_current_user)
):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    project.status = data.status
    await project.save()
