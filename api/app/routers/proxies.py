import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.common.models import orm
from app.dto.common import WorkflowOut
from app.dto.proxy import ProxiesBulkCreateIn, ProxyOut
from app.hatchet.base import models, tasks
from app.routers.auth import get_current_user
from app.routers.sse import watch_job

router = APIRouter(prefix="/proxies", tags=["proxy"])


@router.post("/", response_model=WorkflowOut)
async def upload_proxies(
    input: ProxiesBulkCreateIn,
    user=Depends(get_current_user),
):
    try:
        ref = await tasks.proxies_upload.aio_run_no_wait(
            input=models.ProxiesUploadIn(user_id=user.id, proxies=input.proxies)
        )
        print(ref)
        asyncio.create_task(watch_job(ref.workflow_run_id))
        return {"id": ref.workflow_run_id}
    except Exception as e:
        return JSONResponse({"message": str(e)}, status_code=500)


@router.get("/", response_model=list[ProxyOut])
async def get_proxies(user=Depends(get_current_user)):
    return await ProxyOut.from_queryset(orm.Proxy.filter(user_id=user.id))


@router.delete("/")
async def delete_proxies(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Proxy.filter(id__in=id, user_id=user.id).delete()
