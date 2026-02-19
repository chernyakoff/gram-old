from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.functions import Count

from models import orm
from api.dto.mailing import MailingIn, MailingListOut, MailingOut, RecipientListOut
from api.routers.auth import get_current_user

router = APIRouter(prefix="/mailings", tags=["mailings"])


@router.post("/")
async def create_mailing(data: MailingIn, user=Depends(get_current_user)):
    await data.create_tortoise_instance(orm.Mailing, user_id=user.id)


@router.get("/", response_model=list[MailingOut])
async def get_mailings(user=Depends(get_current_user)):
    qs = (
        orm.Mailing.filter(user_id=user.id)
        .annotate(total_count=Count("recipients"))
        .annotate(
            sent_count=Count(
                "recipients", _filter=Q(recipients__status=orm.RecipientStatus.SENT)
            )
        )
        .annotate(
            failed_count=Count(
                "recipients", _filter=Q(recipients__status=orm.RecipientStatus.FAILED)
            )
        )
    )
    return await MailingOut.from_queryset(qs)


@router.delete("/")
async def delete_mailings(id: list[int] = Query(...), user=Depends(get_current_user)):
    await orm.Mailing.filter(id__in=id, user_id=user.id).delete()


@router.get("/list", response_model=list[MailingListOut])
async def get_mailing_list(user=Depends(get_current_user)):
    return await MailingListOut.from_queryset(orm.Mailing.filter(user_id=user.id))


@router.get("/recipients/list", response_model=list[RecipientListOut])
async def get_recipient_list(user=Depends(get_current_user)):
    qs = (
        orm.Recipient.filter(
            mailing__project__user_id=user.id,
            mailing__user_id=user.id,
            dialog__isnull=False,
        )
        .order_by("username", "id")
    )
    return await RecipientListOut.from_queryset(qs)


class MailingToggleIn(BaseModel):
    active: bool


@router.patch("/{id}/toggle")
async def update_project_status(
    id: int, data: MailingToggleIn, user=Depends(get_current_user)
):
    mailing = await orm.Mailing.get_or_none(id=id, user_id=user.id)
    if not mailing:
        raise HTTPException(status_code=404, detail="not found")

    mailing.active = data.active
    await mailing.save(update_fields=["active"])
