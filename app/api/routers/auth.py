from fastapi import Header, HTTPException, status

from models import orm
from utils.neurousers_api import NeuroUsersApiError, NeuroUsersClient, UserMeResponse


def _extract_bearer_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header missing or invalid")
    return authorization.split(" ", 1)[1]


async def _get_remote_me(authorization: str) -> UserMeResponse:
    token = _extract_bearer_token(authorization)
    try:
        async with NeuroUsersClient() as client:
            return await client.get_me(token)
    except NeuroUsersApiError as exc:
        text = str(exc)
        if " -> 401:" in text or " -> 403:" in text:
            raise HTTPException(401, "Invalid token") from exc
        if " -> 404:" in text:
            raise HTTPException(404, "User not found") from exc
        raise HTTPException(502, "Auth provider unavailable") from exc


async def _sync_local_user(me: UserMeResponse) -> orm.User:
    user, _ = await orm.User.get_or_create(id=me.id)
    return user


async def get_current_user(authorization: str = Header(...)) -> orm.User:
    me = await _get_remote_me(authorization)
    return await _sync_local_user(me)


async def admin_required(authorization: str = Header(...)) -> orm.User:
    me = await _get_remote_me(authorization)
    role = (me.role or "").upper()
    if role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return await _sync_local_user(me)
