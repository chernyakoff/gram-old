# app/router/projects.py

import asyncio
import os
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from tortoise import Tortoise
from tortoise_serializer import ContextType, Serializer

from app.common.models import orm
from app.common.utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    ProjectSkipOptions,
    validate_prompt,
)
from app.common.utils.s3 import AsyncS3Client
from app.config import config
from app.dto.common import WorkflowOut
from app.dto.project import (
    ProjectBase,
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


async def delete_project_files(paths: list[str]):
    async with AsyncS3Client() as s3:  # type: ignore
        await s3.delete_many(paths)


@router.delete("/")
async def delete_projects(id: list[int] = Query(...), user=Depends(get_current_user)):
    files = await orm.ProjectFile.filter(project_id__in=id).all()
    s3paths = [f.storage_path for f in files]
    await orm.Project.filter(id__in=id, user_id=user.id).delete()
    asyncio.create_task(delete_project_files(s3paths))


class ProjectStatusOut(BaseModel):
    result: Literal["success", "error"]
    errors: list[str]


def has_unresolved_template(text: str) -> bool:
    """
    Проверяет наличие неразобранных шаблонов вида {a|b}
    """
    return bool(re.search(r"\{[^{}]*\|[^{}]*\}", text))


@router.patch("/{id}/status", response_model=ProjectStatusOut)
async def update_project_status(
    id: int, data: ProjectStatusIn, user=Depends(get_current_user)
):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    errors = []
    if data.status is True:
        prompt = await orm.Prompt.get_or_none(project_id=id)
        if not validate_prompt(prompt, project.skip_options):
            errors.append("В проекте отсутсвует промпт")
        if not project.first_message:
            errors.append("В проекте отсутсвует первое сообщение")
        if not has_unresolved_template(project.first_message):
            errors.append("Пeрвое сообщение не рандомизировано")
        if errors:
            return ProjectStatusOut(result="error", errors=errors)

    project.status = data.status
    await project.save()
    return ProjectStatusOut(result="success", errors=[])


@router.post("/synonimize", response_model=models.SynonimizeOut)
async def synonimize(data: SynonimizeIn, user=Depends(get_current_user)):
    response = await tasks.synonimize.aio_run(
        models.SynonimizeIn(text=data.text, user_id=user.id)
    )
    return response


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
    premium_required: bool
    first_message: Optional[str] = None


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


# файлы


class ProjectFileIn(BaseModel):
    filename: str
    file_size: int
    storage_path: str
    content_type: str


class ProjectFileOut(Serializer):
    id: int
    title: str
    filename: str
    file_size: int
    url: str
    content_type: str
    status: Optional[orm.ProjectFileStatus] = None

    @classmethod
    async def resolve_url(cls, instance: orm.ProjectFile, context: ContextType) -> str:
        return f"{config.s3.public_endpoint_url}/{instance.storage_path}"


class ProjectFileUpdateIn(BaseModel):
    title: str
    filename: str
    status: Optional[orm.ProjectFileStatus] = None


@router.post("/{id}/files")
async def save_files(
    id: int, data: list[ProjectFileIn], user=Depends(get_current_user)
):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    insert = []
    for file in data:
        insert.append(
            orm.ProjectFile(
                project_id=id,
                filename=file.filename,
                file_size=file.file_size,
                storage_path=file.storage_path,
                content_type=file.content_type,
                title=file.filename.split(".")[0],
            )
        )
    await orm.ProjectFile.bulk_create(insert)


@router.get("/{id}/files", response_model=list[ProjectFileOut])
async def get_files(id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    return await ProjectFileOut.from_queryset(orm.ProjectFile.filter(project_id=id))


@router.delete("/{project_id}/files/{file_id}")
async def delete_file(project_id: int, file_id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=project_id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    file = await orm.ProjectFile.get_or_none(id=file_id)
    if file:
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(file.storage_path)

        await file.delete()


def preserve_extension(old_name: str, new_name: str) -> str:
    # извлекаем расширение старого файла (без точки)
    old_ext = os.path.splitext(old_name)[1]  # вернёт '.txt'

    # извлекаем имя нового файла без расширения
    base_name = os.path.splitext(new_name)[0]

    # собираем обратно
    return f"{base_name}{old_ext}"


@router.post("/{project_id}/files/{file_id}")
async def update_file(
    project_id: int,
    file_id: int,
    data: ProjectFileUpdateIn,
    user=Depends(get_current_user),
):
    project = await orm.Project.filter(user_id=user.id, id=project_id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    file = await orm.ProjectFile.get_or_none(id=file_id)
    if file:
        file.filename = preserve_extension(file.filename, data.filename)
        file.title = data.title
        if data.status:
            file.status = data.status

        await file.save(update_fields=["filename", "title", "status"])


# documents


class ProjectDocumentIn(BaseModel):
    filename: str
    file_size: int
    storage_path: str
    content_type: str


class ProjectDocumentOut(Serializer):
    id: int

    filename: str
    file_size: int
    url: str
    content_type: str

    @classmethod
    async def resolve_url(cls, instance: orm.ProjectFile, context: ContextType) -> str:
        return f"{config.s3.public_endpoint_url}/{instance.storage_path}"


@router.post("/{id}/documents", response_model=WorkflowOut)
async def save_documents(
    id: int, data: list[ProjectDocumentIn], user=Depends(get_current_user)
):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    documents = [models.ProjectDocument(**d.model_dump()) for d in data]

    ref = await tasks.save_documents.aio_run_no_wait(
        input=models.ProjectDocumentsIn(project_id=id, documents=documents)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore
    return {"id": ref.workflow_run_id}


@router.get("/{id}/documents", response_model=list[ProjectDocumentOut])
async def get_documents(id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    return await ProjectDocumentOut.from_queryset(
        orm.ProjectDocument.filter(project_id=id)
    )


@router.delete("/{project_id}/documents/{file_id}")
async def delete_document(
    project_id: int, file_id: int, user=Depends(get_current_user)
):
    project = await orm.Project.filter(user_id=user.id, id=project_id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    file = await orm.ProjectDocument.get_or_none(id=file_id)
    if file:
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(file.storage_path)

        await file.delete()

        await Tortoise.get_connection("default").execute_query(
            "DELETE FROM knowledge_chunks WHERE document_id = $1", [file_id]
        )


# календарь


class Calendar(BaseModel):
    use_calendar: bool
    morning_reminder: Optional[str] = None
    meeting_reminder: Optional[str] = None


@router.get("/{id}/calendar", response_model=Calendar)
async def get_calendar(id: int, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    return Calendar(
        use_calendar=project.use_calendar,
        morning_reminder=project.morning_reminder,
        meeting_reminder=project.meeting_reminder,
    )


@router.post("/{id}/calendar")
async def save_calendarf(id: int, data: Calendar, user=Depends(get_current_user)):
    project = await orm.Project.filter(user_id=user.id, id=id).get_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    project.update_from_dict(data.model_dump())
    await project.save(
        update_fields=["use_calendar", "morning_reminder", "meeting_reminder"]
    )
