from fastapi import Depends, Header, HTTPException, status

from models import orm
from utils.neurousers_api import NeuroUsersApiError, NeuroUsersClient


def _extract_bearer_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header missing or invalid")
    return authorization.split(" ", 1)[1]


async def _get_remote_me(authorization: str):
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


async def _sync_local_user(me) -> orm.User:
    role = orm.Role.ADMIN if me.role.upper() == "ADMIN" else orm.Role.USER
    user = await orm.User.get_or_none(id=me.id)
    if user is None:
        return await orm.User.create(
            id=me.id,
            username=me.username,
            first_name=me.first_name,
            last_name=me.last_name,
            photo_url=me.photo_url,
            role=role,
        )

    await orm.User.filter(id=me.id).update(
        username=me.username,
        first_name=me.first_name,
        last_name=me.last_name,
        photo_url=me.photo_url,
        role=role,
    )
    user.username = me.username
    user.first_name = me.first_name
    user.last_name = me.last_name
    user.photo_url = me.photo_url
    user.role = role
    return user


async def get_current_user(authorization: str = Header(...)) -> orm.User:
    me = await _get_remote_me(authorization)
    return await _sync_local_user(me)


async def get_real_user(authorization: str = Header(...)) -> orm.User:
    return await get_current_user(authorization)


def admin_required(user: orm.User = Depends(get_real_user)) -> orm.User:
    if user.role != orm.Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
