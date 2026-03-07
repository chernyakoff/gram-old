import asyncio

from aerich import Tortoise
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from tortoise.query_utils import Prefetch

from app.common.models import orm
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


async def has_mobile_proxy(user_id: int) -> bool:
    return await orm.MobProxy.filter(user_id=user_id, active=True).exists()


@router.post("/", response_model=WorkflowOut)
async def upload_accounts(
    input: AccountsBulkCreateIn,
    user=Depends(get_current_user),
):
    try:
        task = (
            tasks.accounts_upload_mp
            if await has_mobile_proxy(user.id)
            else tasks.accounts_upload
        )
        ref = await task.aio_run_no_wait(
            input=models.AccountsUploadIn(
                user_id=user.id,
                concurrency_key=str(user.id),
                s3path=input.s3path,
            ),
        )
        asyncio.create_task(watch_job(ref.workflow_run_id))
        return {"id": ref.workflow_run_id}
    except Exception as e:
        return JSONResponse({"message": str(e)}, status_code=500)


@router.get("/list", response_model=list[AccountListOut])
async def get_account_list(user=Depends(get_current_user)):
    return await AccountListOut.from_queryset(orm.Account.filter(user_id=user.id))


@router.get("/{id}", response_model=AccountOut)
async def get_account(id: int, user=Depends(get_current_user)):
    account = await orm.Account.get(id=id).prefetch_related("photos")
    if not account:
        raise HTTPException(status_code=404, detail="not found")
    return await AccountOut.from_tortoise_orm(account)


@router.get("/", response_model=list[AccountOut])
async def get_accounts(user=Depends(get_current_user)):
    qs = orm.Account.filter(user_id=user.id).prefetch_related(
        Prefetch(
            "photos",
            queryset=orm.AccountPhoto.filter(main=True),
        ),
        "project",
    )

    # 🔽 Получаем id аккаунтов одним лёгким запросом
    account_ids = await qs.values_list("id", flat=True)

    rows = await Tortoise.get_connection("default").execute_query_dict(
        """
        SELECT account_id, COUNT(DISTINCT DATE(started_at)) AS active_days
        FROM dialogs
        WHERE account_id = ANY($1)
        GROUP BY account_id
        """,
        [account_ids],
    )

    active_days_map = {r["account_id"]: r["active_days"] for r in rows}

    return await AccountOut.from_queryset(
        qs,
        context={"active_days_map": active_days_map},
    )


async def delete_accounts_photos(paths: list[str]):
    async with AsyncS3Client() as s3:  # type: ignore
        await s3.delete_many(paths)


@router.delete("/")
async def delete_accounts(id: list[int] = Query(...), user=Depends(get_current_user)):
    photos = await orm.AccountPhoto.filter(account_id__in=id).all()
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
    params["concurrency_key"] = str(user.id)
    task = (
        tasks.accounts_update_mp
        if await has_mobile_proxy(user.id)
        else tasks.accounts_update
    )
    ref = await task.aio_run_no_wait(
        input=models.AccountsUpdateIn(**params),
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))
    return {"id": ref.workflow_run_id}


@router.post("/bind-project")
async def bind_project(data: BindProjectIn, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=data.project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")

    await orm.Account.filter(
        id__in=data.account_ids, user_id=user.id, premium=True
    ).update(project_id=data.project_id)


@router.post("/{id}/premium", response_model=models.BuyPremiumOut)
async def buy_premium(id: int, card: CardDetails, user=Depends(get_current_user)):
    account = await orm.Account.get_or_none(user_id=user.id, id=id)
    if not account:
        raise HTTPException(status_code=404, detail="not found")

    input_model = models.BuyPremiumIn(
        account_id=id,
        user_id=user.id,
        concurrency_key=str(user.id),
        card=models.CardDetails(**card.model_dump()),
    )
    task = (
        tasks.buy_premium_mp
        if await has_mobile_proxy(user.id)
        else tasks.buy_premium
    )
    response = await task.aio_run(input=input_model)
    return response


@router.post("/check", response_model=WorkflowOut)
async def check(data: AccountsCheckIn, user=Depends(get_current_user)):
    accounts = await orm.Account.filter(id__in=data.account_ids, user_id=user.id).all()
    ids = [a.id for a in accounts]
    task = (
        tasks.accounts_check_mp
        if await has_mobile_proxy(user.id)
        else tasks.accounts_check
    )
    ref = await task.aio_run_no_wait(
        input=models.AccountsCheckIn(
            user_id=user.id,
            concurrency_key=str(user.id),
            ids=ids,
        ),
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))
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

    task = (
        tasks.stop_premium_mp
        if await has_mobile_proxy(user.id)
        else tasks.stop_premium
    )
    ref = await task.aio_run_no_wait(
        input=models.StopPremiumIn(
            account_id=id,
            user_id=user.id,
            concurrency_key=str(user.id),
        ),
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))
    return {"id": ref.workflow_run_id}
