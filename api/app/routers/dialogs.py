from fastapi import APIRouter, Depends

from app.common.models import orm
from app.dto.dialog import DialogMessageOut, DialogOut
from app.routers.auth import get_current_user

router = APIRouter(prefix="/dialogs", tags=["dialogs"])


@router.get("/", response_model=list[DialogOut])
async def get_dialogs(user=Depends(get_current_user)):
    return await DialogOut.from_queryset(
        orm.Dialog.filter(recipient__mailing__user_id=user.id)
        .prefetch_related("recipient", "recipient__mailing")
        .order_by("-started_at")
    )


@router.get("/{id}", response_model=list[DialogMessageOut])
async def get_dialiog(id: int, user=Depends(get_current_user)):
    messages = await orm.Message.filter(dialog_id=id).order_by("id").all()
    return [DialogMessageOut(sender=m.sender, text=m.text) for m in messages]
