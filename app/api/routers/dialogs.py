from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from jose import JWTError, jwt
from tortoise import Tortoise

from api.dto.dialog import DialogIn, DialogMessageOut, DialogOut, DialogSystemMessageIn
from api.routers.auth import get_current_user
from config import config
from models import orm
from utils.notify import build_dialog_text

router = APIRouter(prefix="/dialogs", tags=["dialogs"])


async def _get_dialogs(
    user_id: int,
    project_id: int | None = None,
    account_id: int | None = None,
    mailing_id: int | None = None,
    recipient_id: int | None = None,
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
  AND ($5::bigint IS NULL OR r.id = $5)
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
            recipient_id,
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


def decode_dialog_share_token(token: str) -> tuple[int, int]:
    try:
        payload = jwt.decode(
            token, config.api.jwt.secret, algorithms=[config.api.jwt.algorithm]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid link")

    if payload.get("scope") != "dialog_share":
        raise HTTPException(status_code=401, detail="Invalid link")

    user_id = payload.get("sub")
    dialog_id = payload.get("dialog_id")
    if not user_id or dialog_id is None:
        raise HTTPException(status_code=401, detail="Invalid link")

    try:
        return int(user_id), int(dialog_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid link")


async def _get_dialog_messages_for_user(
    *, dialog_id: int, user_id: int
) -> list[DialogMessageOut]:
    owned = await _is_dialog_owned_by_user(dialog_id=dialog_id, user_id=user_id)
    if not owned:
        raise HTTPException(status_code=404, detail="Dialog not found")

    messages = await orm.Message.filter(dialog_id=dialog_id).order_by("id").all()
    return [
        DialogMessageOut(
            sender=m.sender, text=m.text, created_at=m.created_at, ack=m.ack
        )
        for m in messages
    ]


async def _is_dialog_owned_by_user(*, dialog_id: int, user_id: int) -> bool:
    owned = await orm.Dialog.filter(
        id=dialog_id,
        recipient__mailing__user_id=user_id,
    ).exists()
    return owned


@router.get("/shared/{token}")
async def get_shared_dialog(token: str):
    user_id, dialog_id = decode_dialog_share_token(token)
    owned = await _is_dialog_owned_by_user(dialog_id=dialog_id, user_id=user_id)
    if not owned:
        raise HTTPException(status_code=404, detail="Dialog not found")
    text = await build_dialog_text(dialog_id)
    return PlainTextResponse(text, media_type="text/plain; charset=utf-8")


@router.get("/{id:int}", response_model=list[DialogMessageOut])
async def get_dialiog(id: int, user=Depends(get_current_user)):
    return await _get_dialog_messages_for_user(dialog_id=id, user_id=user.id)


@router.post("/add", response_model=list[DialogMessageOut])
async def system(data: DialogSystemMessageIn, user=Depends(get_current_user)):
    owned = await orm.Dialog.filter(
        id=data.dialog_id, recipient__mailing__user_id=user.id
    ).exists()
    if not owned:
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
