import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.common.models import orm
from app.dto.common import WorkflowOut
from app.dto.proxy import (
    ProxiesBulkCreateIn,
    ProxiesCheckIn,
    ProxiesCountryIn,
    ProxyOut,
)
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
            input=models.ProxiesUploadIn(user_id=user.id, proxies=input.proxies),
        )
        asyncio.create_task(watch_job(ref.workflow_run_id))
        return {"id": ref.workflow_run_id}
    except Exception as e:
        return JSONResponse({"message": str(e)}, status_code=500)


@router.get("/", response_model=list[ProxyOut])
async def get_proxies(user=Depends(get_current_user)):
    return await ProxyOut.from_queryset(
        orm.Proxy.filter(user_id=user.id).prefetch_related("account")
    )


@router.delete("/")
async def delete_proxies(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Proxy.filter(id__in=id, user_id=user.id).delete()


@router.post("/country")
async def change_country(
    data: ProxiesCountryIn,
    user=Depends(get_current_user),
):
    updated = await orm.Proxy.filter(id__in=data.ids, user_id=user.id).update(
        country=data.country
    )

    if updated == 0:
        raise HTTPException(status_code=404, detail="not found")

    return {"updated": updated}


@router.post("/check", response_model=WorkflowOut)
async def check(data: ProxiesCheckIn, user=Depends(get_current_user)):
    proxies = await orm.Proxy.filter(id__in=data.ids, user_id=user.id).all()
    ids = [p.id for p in proxies]
    ref = await tasks.proxies_check.aio_run_no_wait(
        input=models.ProxiesCheckIn(ids=ids),
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))
    return {"id": ref.workflow_run_id}
