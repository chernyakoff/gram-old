import asyncio
from datetime import datetime
from typing import Self

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tortoise.query_utils import Prefetch

from app.common.models import orm
from app.common.utils.functions import pick
from app.common.utils.s3 import AsyncS3Client
from app.config import config
from app.hatchet import models, tasks
from app.routers.auth import get_current_user
from app.routers.sse import watch_job

router = APIRouter(prefix="/accounts", tags=["account"])


class WorkflowOut(BaseModel):
    id: str


class AccountsUploadIn(BaseModel):
    s3path: str


class AccountPhotosIn(BaseModel):
    delete: list[int]
    upload: list[str]


class AccountIn(BaseModel):
    username: str | None
    about: str | None
    channel: str | None
    first_name: str | None
    last_name: str | None
    about: str | None = None
    photos: AccountPhotosIn


class AccountPhoto(BaseModel):
    id: int
    url: str


class AccountOut(BaseModel):
    id: int
    phone: str
    country: str
    created_at: datetime
    active: bool
    busy: bool
    premium: bool
    username: str | None
    about: str | None
    channel: str | None
    first_name: str | None
    last_name: str | None
    twofa: str | None
    avatar: str | None = None
    photos: list[AccountPhoto] | None = None

    @classmethod
    def from_orm(
        cls, account: orm.Account, photos: list[orm.AccountPhoto] = []
    ) -> Self:
        params = pick(
            [
                "id",
                "phone",
                "country",
                "created_at",
                "active",
                "busy",
                "premium",
                "username",
                "avatar",
                "about",
                "channel",
                "first_name",
                "last_name",
                "twofa",
            ],
            account,
        )
        params["photos"] = []
        if photos:
            params["photos"].extend(
                [
                    AccountPhoto(url=f"{config.s3.endpoint_url}/{p.path}", id=p.id)
                    for p in photos
                ]
            )

        return cls(**params)


@router.post("/", response_model=WorkflowOut)
async def upload_accounts(
    input: AccountsUploadIn,
    user=Depends(get_current_user),
):
    try:
        ref = await tasks.accounts_upload.aio_run_no_wait(
            input=models.AccountsUploadIn(user_id=user.id, s3path=input.s3path)
        )
        asyncio.create_task(watch_job(ref.workflow_run_id))
        return {"id": ref.workflow_run_id}
    except Exception as e:
        return JSONResponse({"message": str(e)}, status_code=500)


@router.get("/{id}", response_model=AccountOut)
async def get_account(id: int, user=Depends(get_current_user)):
    account = await orm.Account.filter(id=id).first()
    print(account)
    if not account:
        raise HTTPException(status_code=404, detail="not found")
    photos = await orm.AccountPhoto.filter(account_id=account.id).all()

    return AccountOut.from_orm(account, photos)


@router.get("/", response_model=list[AccountOut])
async def get_accounts(user=Depends(get_current_user)):
    accounts = (
        await orm.Account.filter(user_id=user.id)
        .prefetch_related(
            Prefetch(
                "photos",
                queryset=orm.AccountPhoto.filter(main=True),
                to_attr="main_photos",  # сохраняем результат в атрибуте main_photo
            )
        )
        .all()
    )
    result = []
    for orm_account in accounts:
        photos = []
        if orm_account.main_photos:
            photos.append(orm_account.main_photos[0])
        account = AccountOut.from_orm(orm_account, photos)
        result.append(account)
    return result


async def delete_accounts_photos(paths: list[str]):
    async with AsyncS3Client() as s3:
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
    ref = await tasks.accounts_update.aio_run_no_wait(
        input=models.AccountsUpdateIn(**params)
    )
    asyncio.create_task(watch_job(ref.workflow_run_id))
    return {"id": ref.workflow_run_id}
