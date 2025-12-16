from datetime import timedelta

from aerich import Tortoise
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
    rows = await Tortoise.get_connection("default").execute_query_dict(
        """
SELECT 
    d.id AS dialog_id,
    d.status AS status,
    d.started_at AS started_at,
    r.username AS recipient_username,
    COALESCE(a.username, 'N/A') AS account_username,
    p.name AS project_name,
    COUNT(m.id) AS msg_count,
    MAX(m.created_at) AS last_msg_at
FROM dialogs d
JOIN recipients r ON r.id = d.recipient_id
JOIN mailings ml ON ml.id = r.mailing_id
LEFT JOIN projects p ON p.id = ml.project_id
LEFT JOIN accounts a ON a.id = d.account_id
LEFT JOIN messages m ON m.dialog_id = d.id
WHERE ml.user_id = $1
GROUP BY d.id, d.status, d.started_at, r.username, a.username, p.name
HAVING NOT (
    d.status = 'init' AND
    MAX(m.created_at) < NOW() - INTERVAL '3 days' AND
    COUNT(m.id) < 3
)
ORDER BY last_msg_at DESC NULLS LAST, d.started_at DESC
""",
        [user.id],
    )
    return [
        DialogOut(
            id=r["dialog_id"],
            status=r["status"],
            recipient=r["recipient_username"],
            account=r["account_username"],
            project=r["project_name"],
            started_at=r["started_at"],
        )
        for r in rows
    ]


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
