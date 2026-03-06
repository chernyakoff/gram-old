import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.functions import Count

from models import orm
from api.dto.mailing import (
    MailingChangeProjectIn,
    MailingIn,
    MailingListOut,
    MailingOut,
    RecipientListOut,
)
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


async def _next_split_name(user_id: int, project_id: int, base_name: str) -> str:
    names = await orm.Mailing.filter(
        user_id=user_id,
        project_id=project_id,
        name__startswith=f"{base_name} (",
    ).values_list("name", flat=True)

    pattern = re.compile(rf"^{re.escape(base_name)} \((\d+)\)$")
    used = set()
    for name in names:
        match = pattern.match(name or "")
        if match:
            used.add(int(match.group(1)))

    suffix = 1
    while suffix in used:
        suffix += 1

    return f"{base_name} ({suffix})"


@router.post("/change-project")
async def change_project(data: MailingChangeProjectIn, user=Depends(get_current_user)):
    mailing = await orm.Mailing.get_or_none(id=data.mailing_id, user_id=user.id)
    if not mailing:
        raise HTTPException(status_code=404, detail="mailing not found")

    project = await orm.Project.get_or_none(id=data.project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    pending = await orm.Recipient.filter(
        mailing_id=mailing.id,
        status=orm.RecipientStatus.PENDING,
    ).all()
    if not pending:
        raise HTTPException(status_code=400, detail="pending recipients not found")

    base_name = (mailing.name or "").strip() or "Рассылка"
    name = await _next_split_name(
        user_id=user.id,
        project_id=project.id,
        base_name=base_name,
    )

    new_mailing = await orm.Mailing.create(
        name=name,
        project_id=project.id,
        user_id=user.id,
        status=orm.MailingStatus.DRAFT,
        active=False,
    )

    recipients = [
        orm.Recipient(
            mailing_id=new_mailing.id,
            access_hash=recipient.access_hash,
            peer_id=recipient.peer_id,
            username=recipient.username,
            first_name=recipient.first_name,
            last_name=recipient.last_name,
            phone=recipient.phone,
            about=recipient.about,
            channel=recipient.channel,
            premium=recipient.premium,
            metadata=recipient.metadata,
            status=orm.RecipientStatus.PENDING,
            lease_expires_at=recipient.lease_expires_at,
            attempts=recipient.attempts,
            last_error=recipient.last_error,
            last_attempt_at=recipient.last_attempt_at,
        )
        for recipient in pending
    ]
    await orm.Recipient.bulk_create(recipients, batch_size=1000)


@router.patch("/{id}/toggle")
async def update_project_status(
    id: int, data: MailingToggleIn, user=Depends(get_current_user)
):
    mailing = await orm.Mailing.get_or_none(id=id, user_id=user.id)
    if not mailing:
        raise HTTPException(status_code=404, detail="not found")

    mailing.active = data.active
    await mailing.save(update_fields=["active"])
