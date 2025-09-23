import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Self

import pytz
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel

from app.common.models import orm
from app.common.utils.functions import pick
from app.config import config

moscow_tz = pytz.timezone("Europe/Moscow")


router = APIRouter(prefix="/auth", tags=["auth"])


# ----------------- Schemas -----------------


class UserLoginIn(BaseModel):
    id: int
    auth_date: int
    hash: str
    first_name: str | None
    last_name: str | None
    username: str | None
    photo_url: str | None


class UserLoginOut(BaseModel):
    access_token: str


class UserMeOut(BaseModel):
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    photo_url: str | None
    role: str
    has_license: bool

    @classmethod
    def from_orm(cls, user: orm.User) -> Self:
        return cls(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            photo_url=user.photo_url,
            role=user.role.name,
            has_license=bool(
                user.license_end_date
                and user.license_end_date > datetime.now(moscow_tz)
            ),
        )


# ----------------- Telegram validation -----------------


def validate_telegram_data(data: dict):
    received_hash = data.pop("hash", None)
    auth_date = data.get("auth_date")

    if not received_hash:
        raise HTTPException(400, "No hash in Telegram data")

    if auth_date is None or int(time.time()) - int(auth_date) > 86400:
        raise HTTPException(400, "Telegram authentication session is expired.")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(
        config.api.bot.token.get_secret_value().encode()
    ).digest()
    generated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_hash, received_hash):
        raise HTTPException(400, "Telegram data signature mismatch")


# ----------------- JWT helpers -----------------


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        seconds=config.api.jwt.expire_seconds
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, config.api.jwt.secret, algorithm=config.api.jwt.algorithm
    )


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=config.api.jwt.refresh_expire_days
    )
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, config.api.jwt.secret, algorithm=config.api.jwt.algorithm
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, config.api.jwt.secret, algorithms=[config.api.jwt.algorithm]
        )
    except ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except JWTError:
        raise HTTPException(401, "Invalid token")


def set_refresh_cookie(response: Response, user_id: int):
    refresh_token = create_refresh_token({"sub": str(user_id)})
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="none" if config.web.url.startswith("https") else "lax",
        secure=True if config.web.url.startswith("https") else False,
        max_age=config.api.jwt.refresh_expire_days * 24 * 60 * 60,
        path="/",
    )


async def get_user_from_token(token: str) -> orm.User | None:
    payload = decode_token(token)
    user_id = int(payload.get("sub"))  # type:ignore
    return await orm.User.get_or_none(id=user_id)


async def get_current_user(authorization: str = Header(...)) -> orm.User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authorization header missing or invalid")
    token = authorization.split(" ", 1)[1]
    user = await get_user_from_token(token)

    if not user:
        raise HTTPException(404, "User not found")
    return user


# ----------------- Auth endpoints -----------------


@router.post("/", response_model=UserLoginOut)
async def login(data: UserLoginIn, response: Response):
    validate_telegram_data(data.model_dump())

    user, _ = await orm.User.update_or_create(
        id=data.id,
        defaults=pick(["username", "first_name", "last_name", "photo_url"], data),
    )

    access_token = create_access_token({"sub": str(user.id)})
    set_refresh_cookie(response, user.id)

    return {"access_token": access_token}


@router.get("/me", response_model=UserMeOut)
async def me(user=Depends(get_current_user)) -> UserMeOut:
    return UserMeOut.from_orm(user)


@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie(key="refresh_token", path="/")
    return {"detail": "Logged out successfully"}


@router.post("/refresh", response_model=UserLoginOut)
async def refresh_token_endpoint(
    response: Response, refresh_token: Optional[str] = Cookie(None)
):
    if not refresh_token:
        raise HTTPException(401, "No refresh token cookie found")

    user = await get_user_from_token(refresh_token)
    if not user:
        raise HTTPException(404, "User not found")

    access_token = create_access_token({"sub": str(user.id)})
    set_refresh_cookie(response, user.id)

    return {"access_token": access_token}
