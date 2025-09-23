import asyncio
from datetime import datetime
from typing import Self

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.common.models import orm
from app.hatchet import models, tasks
from app.hatchet.client import hatchet
from app.routers.auth import get_current_user
from app.routers.sse import watch_job

router = APIRouter(prefix="/proxies", tags=["proxy"])


class ProxiesUploadIn(BaseModel):
    s3path: str


class WorkflowOut(BaseModel):
    id: str


class ProxyOut(BaseModel):
    id: int
    host: str
    port: int
    username: str
    password: str
    country: str
    created_at: datetime

    @classmethod
    def from_orm(cls, proxy: orm.Proxy) -> Self:
        return cls(
            id=proxy.id,
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=proxy.password,
            country=proxy.country,
            created_at=proxy.created_at,
        )


@router.post("/", response_model=WorkflowOut)
async def upload_proxies(
    input: ProxiesUploadIn,
    user=Depends(get_current_user),
):
    try:
        ref = await tasks.proxies_upload.aio_run_no_wait(
            input=models.ProxiesUploadIn(user_id=user.id, s3path=input.s3path)
        )
        asyncio.create_task(watch_job(ref.workflow_run_id))
        return {"id": ref.workflow_run_id}
    except Exception as e:
        return JSONResponse({"message": str(e)}, status_code=500)


@router.get("/upload-progress/{run_id}")
async def proxies_progress(run_id: str):
    async def event_generator():
        async for chunk in hatchet.runs.subscribe_to_stream(run_id):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/", response_model=list[ProxyOut])
async def get_proxies(user=Depends(get_current_user)):
    proxies = await orm.Proxy.filter(user_id=user.id).all()
    return [ProxyOut.from_orm(p) for p in proxies]


@router.delete("/")
async def delete_proxies(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Proxy.filter(id__in=id, user_id=user.id).delete()
