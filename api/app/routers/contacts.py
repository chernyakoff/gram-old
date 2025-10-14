from fastapi import APIRouter, Depends, HTTPException, Query

from app.common.models import orm
from app.common.utils.validators import is_valid_telegram_username
from app.dto.contact import (
    ContactOut,
    ContactsBulkCreateIn,
    ContactsBulkCreateOut,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("/", response_model=ContactsBulkCreateOut)
async def create_contacts(data: ContactsBulkCreateIn, user=Depends(get_current_user)):
    project = await orm.Project.get_or_none(id=data.project_id, user_id=user.id)
    if not project:
        raise HTTPException(status_code=404, detail="not found")
    contacts = [
        orm.Contact(username=u, project_id=data.project_id, user_id=user.id)
        for u in data.usernames
        if is_valid_telegram_username(u)
    ]
    count_before = await orm.Contact.filter(project_id=project.id).count()
    await orm.Contact.bulk_create(contacts, ignore_conflicts=True, batch_size=1000)
    count_after = await orm.Contact.filter(project_id=project.id).count()
    return {"total": len(data.usernames), "added": count_after - count_before}


@router.get("/", response_model=list[ContactOut])
async def get_contacts(user=Depends(get_current_user)):
    return await ContactOut.from_queryset(orm.Contact.filter(project__user_id=user.id))


@router.delete("/")
async def delete_contacts(uid: list[int] = Query(...), user=Depends(get_current_user)):
    uids = await orm.Contact.filter(uid__in=uid, project__user_id=user.id).values_list(
        "uid", flat=True
    )
    if not uids:
        raise HTTPException(status_code=404, detail="Contacts not found or not yours")
    await orm.Contact.filter(uid__in=uids).delete()
