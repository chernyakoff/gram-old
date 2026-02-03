import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from tortoise.functions import Count
from tortoise.query_utils import Prefetch

from app.common.models import enums, orm
from app.common.utils.s3 import AsyncS3Client
from app.dto.account import (
    AccountIn,
    AccountListOut,
    AccountOut,
    AccountsBulkCreateIn,
    AccountsCheckIn,
    BindProjectIn,
    SetLimitIn,
)
from app.dto.card import CardDetails
from app.dto.common import WorkflowOut
from app.hatchet.base import models, tasks
from app.routers.auth import get_current_user
from app.routers.sse import watch_job

router = APIRouter(prefix="/accounts", tags=["account"])


@router.post("/", response_model=WorkflowOut)
async def upload_accounts(
    input: AccountsBulkCreateIn,
    user=Depends(get_current_user),
):
    try:
        ref = await tasks.accounts_upload.aio_run_no_wait(
            input=models.AccountsUploadIn(user_id=user.id, s3path=input.s3path)
        )
        asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore
        return {"id": ref.workflow_run_id}
    except Exception as e:
        return JSONResponse({"message": str(e)}, status_code=500)


@router.get("/list", response_model=list[AccountListOut])
async def get_account_list(user=Depends(get_current_user)):
    return await AccountListOut.from_queryset(orm.Account.filter(user_id=user.id))


@router.get("/{id}", response_model=AccountOut)
async def get_account(id: int, user=Depends(get_current_user)):
    account = (
        await orm.Account.get(id=id)
        .prefetch_related("photos", "project")
        .annotate(dialogs_count=Count("dialogs"))
    )
    if not account:
        raise HTTPException(status_code=404, detail="not found")

    return await AccountOut.from_tortoise_orm(account)


@router.get("/", response_model=list[AccountOut])
async def get_accounts(user=Depends(get_current_user)):
    qs = (
        orm.Account.filter(user_id=user.id)
        .prefetch_related(
            Prefetch("photos", queryset=orm.AccountPhoto.filter(main=True)),
            "project",
        )
        .annotate(dialogs_count=Count("dialogs"))
    )
    return await AccountOut.from_queryset(qs)


async def delete_accounts_photos(paths: list[str]):
    async with AsyncS3Client() as s3:  # type: ignore
        await s3.delete_many(paths)


async def save_to_muted(ids: list[int]):
    muted = await orm.Account.filter(id__in=ids, status=enums.AccountStatus.MUTED).all()
    if muted:
        insert = [orm.MutedAccount.from_account(m) for m in muted]
        await orm.MutedAccount.bulk_create(insert, ignore_conflicts=True)


@router.delete("/")
async def delete_accounts(id: list[int] = Query(...), user=Depends(get_current_user)):
    photos = await orm.AccountPhoto.filter(account_id__in=id).all()
    await save_to_muted(id)
    await orm.Account.filter(id__in=id, user_id=user.id).delete()
    asyncio.create_task(delete_accounts_photos([p.path for p in photos]))


@router.patch("/{id}", response_model=WorkflowOut)
async def update_accounts(
    id: int,
    input: AccountIn,
    user=Depends(get_current_user),
):
    params = input.model_dump()
    params["id"] = id
    params["user_id"] = user.id
    ref = await tasks.accounts_update.aio_run_no_wait(
        input=models.AccountsUpdateIn(**params)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore
    return {"id": ref.workflow_run_id}


@router.post("/bind-project")
async def bind_project(data: BindProjectIn, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=data.project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    await orm.Account.filter(id__in=data.account_ids, user_id=user.id).update(
        project_id=data.project_id
    )


@router.post("/{id}/premium", response_model=models.BuyPremiumOut)
async def buy_premium(id: int, card: CardDetails, user=Depends(get_current_user)):
    account = await orm.Account.get_or_none(user_id=user.id, id=id)
    if not account:
        raise HTTPException(status_code=404, detail="not found")

    input_model = models.BuyPremiumIn(
        account_id=id, card=models.CardDetails(**card.model_dump())
    )
    response = await tasks.buy_premium.aio_run(input=input_model)
    return response


@router.post("/check", response_model=WorkflowOut)
async def check(data: AccountsCheckIn, user=Depends(get_current_user)):
    accounts = await orm.Account.filter(id__in=data.account_ids, user_id=user.id).all()
    ids = [a.id for a in accounts]
    ref = await tasks.accounts_check.aio_run_no_wait(
        input=models.AccountsCheckIn(ids=ids)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore
    return {"id": ref.workflow_run_id}


@router.post("/set-limit")
async def set_limit(data: SetLimitIn, user=Depends(get_current_user)):
    await orm.Account.filter(id__in=data.account_ids, user_id=user.id).update(
        out_daily_limit=data.out_daily_limit
    )


@router.get("/{id}/stop-premium", response_model=WorkflowOut)
async def stop_premium(id: int, user=Depends(get_current_user)):
    account = await orm.Account.get_or_none(user_id=user.id, id=id)
    if not account:
        raise HTTPException(status_code=404, detail="not found")

    ref = await tasks.stop_premium.aio_run_no_wait(
        input=models.StopPremiumIn(account_id=id)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))  # type: ignore
    return {"id": ref.workflow_run_id}
