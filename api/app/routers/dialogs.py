from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from tortoise import timezone as tz
from tortoise.expressions import Q
from tortoise.functions import Count, Max

from app.common.models import enums, orm
from app.dto.dialog import DialogMessageOut, DialogOut, DialogSystemMessageIn
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dialogs", tags=["dialogs"])


@router.get("/", response_model=list[DialogOut])
async def get_dialogs(user=Depends(get_current_user)):
    three_days_ago = tz.now() - timedelta(days=3)

    qs = (
        orm.Dialog.filter(recipient__mailing__user_id=user.id)
        .annotate(
            last_msg_at=Max("messages__created_at"),
            msg_count=Count("messages"),
        )
        .exclude(
            Q(
                finished_at__isnull=False,
                finished_at__lt=three_days_ago,  # старее 3 дней
                status=enums.DialogStatus.INIT,  # status = init
                msg_count__lt=4,  # сообщений < 3
            )
        )
        .prefetch_related(
            "recipient", "recipient__mailing", "recipient__mailing__project", "account"
        )
        .order_by("-last_msg_at", "-started_at")
    )

    return await DialogOut.from_queryset(qs)


@router.get("/{id}", response_model=list[DialogMessageOut])
async def get_dialiog(id: int, user=Depends(get_current_user)):
    messages = await orm.Message.filter(dialog_id=id).order_by("id").all()
    return [
        DialogMessageOut(
            sender=m.sender, text=m.text, created_at=m.created_at, ack=m.ack
        )
        for m in messages
    ]


@router.post("/add", response_model=list[DialogMessageOut])
async def system(data: DialogSystemMessageIn, user=Depends(get_current_user)):
    if not await orm.Dialog.filter(id=data.dialog_id).exists():
        raise HTTPException(status_code=404, detail="Dialog not found")

    await orm.Message.create(
        dialog_id=data.dialog_id, sender=enums.MessageSender.SYSTEM, text=data.message
    )

    # Исправлено: было `id`, должно быть `data.dialog_id`
    messages = await orm.Message.filter(dialog_id=data.dialog_id).order_by("id").all()
    return [
        DialogMessageOut(
            sender=m.sender, text=m.text, created_at=m.created_at, ack=m.ack
        )
        for m in messages
    ]
