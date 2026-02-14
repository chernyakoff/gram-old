from fastapi import APIRouter, Depends, HTTPException
from tortoise import Tortoise

from api.dto.dialog import DialogIn, DialogMessageOut, DialogOut, DialogSystemMessageIn
from api.routers.auth import get_current_user
from models import orm

router = APIRouter(prefix="/dialogs", tags=["dialogs"])


async def _get_dialogs(
    user_id: int,
    project_id: int | None = None,
    account_id: int | None = None,
    mailing_id: int | None = None,
) -> list[dict]:
    return await Tortoise.get_connection("default").execute_query_dict(
        """
SELECT 
    d.id AS dialog_id,
    d.status AS status,
    d.started_at AS started_at,
    r.username AS recipient_username,
    COALESCE(a.username, a.phone) AS account_username,
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
  AND ($2::int IS NULL OR ml.project_id = $2)
  AND ($3::bigint IS NULL OR d.account_id = $3)
  AND ($4::int IS NULL OR ml.id = $4)
GROUP BY 
    d.id,
    d.status,
    d.started_at,
    r.username,
    a.username,
    a.phone,
    p.name
ORDER BY 
    last_msg_at DESC NULLS LAST,
    d.started_at DESC;
    """,
        [
            user_id,
            project_id,
            account_id,
            mailing_id,
        ],
    )


@router.post("/", response_model=list[DialogOut])
async def get_dialogs(payload: DialogIn, user=Depends(get_current_user)):
    params = payload.model_dump()
    params["user_id"] = user.id
    rows = await _get_dialogs(**params)
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
        dialog_id=data.dialog_id, sender=orm.MessageSender.SYSTEM, text=data.message
    )

    # Исправлено: было `id`, должно быть `data.dialog_id`
    messages = await orm.Message.filter(dialog_id=data.dialog_id).order_by("id").all()
    return [
        DialogMessageOut(
            sender=m.sender, text=m.text, created_at=m.created_at, ack=m.ack
        )
        for m in messages
    ]
