from fastapi import APIRouter, Depends, HTTPException, Query

from app.common.models import orm
from app.dto.project import (
    ProjectBase,
    ProjectIn,
    ProjectOut,
    ProjectShortOut,
    ProjectStatusIn,
    create_default_project,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/")
async def create_project(data: ProjectIn, user=Depends(get_current_user)):
    project = orm.Project(**await data.to_model_dict())
    project.user_id = user.id
    await project.save()


@router.get("/", response_model=list[ProjectShortOut])
async def get_projects(user=Depends(get_current_user)):
    return await ProjectShortOut.from_queryset(orm.Project.filter(user_id=user.id))


@router.get("/default", response_model=ProjectIn)
async def get_default_project(user=Depends(get_current_user)):
    return await create_default_project()


@router.get("/list", response_model=list[ProjectBase])
async def get_project_list(user=Depends(get_current_user)):
    return await ProjectBase.from_queryset(orm.Project.filter(user_id=user.id))


@router.get("/{id}", response_model=ProjectOut)
async def get_project(id: int, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    return ProjectOut.from_orm(project)


@router.delete("/")
async def delete_projects(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Project.filter(id__in=id, user_id=user.id).delete()


@router.patch("/{id}")
async def update_project(id: int, data: ProjectIn, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    project.update_from_dict(await data.to_model_dict())
    project.user_id = user.id
    await project.save()


@router.patch("/{id}/status")
async def update_project_status(
    id: int, data: ProjectStatusIn, user=Depends(get_current_user)
):
    project = await orm.Project.get_or_none(id=id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    project.update_from_dict(data.model_dump())
    await project.save()
