from fastapi import APIRouter, Depends, Query
from tortoise.expressions import Q
from tortoise.functions import Count

from app.common.models import orm
from app.dto.mailing import MailingIn, MailingListOut, MailingOut
from app.routers.auth import get_current_user

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
async def get_project_list(user=Depends(get_current_user)):
    return await MailingListOut.from_queryset(orm.Mailing.filter(user_id=user.id))
