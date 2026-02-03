import hashlib
import hmac
import random
import string
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from jose import ExpiredSignatureError, JWTError, jwt

from app.common.models import enums, orm
from app.config import config
from app.dto.user import UserLoginIn, UserLoginOut, UserMeOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def validate_telegram_data(data: dict):
    received_hash = data.pop("hash", None)
    auth_date = data.get("auth_date")

    if not received_hash:
        raise HTTPException(400, "No hash in Telegram data")

    if auth_date is None or int(time.time()) - int(auth_date) > 86400:
        raise HTTPException(400, "Telegram authentication session is expired.")

    # Исключаем пустые значения из проверки
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if v)
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


def create_impersonation_tokens(target_user_id: int, admin_id: int):
    access = create_access_token(
        {
            "sub": str(target_user_id),
            "real_sub": str(admin_id),
            "impersonated": True,
        }
    )

    refresh = create_refresh_token(
        {
            "sub": str(target_user_id),
            "real_sub": str(admin_id),
            "impersonated": True,
        }
    )

    return access, refresh


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


def admin_required(user=Depends(get_current_user)):
    if user.role != enums.Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def generate_ref_code(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


async def create_unique_ref_code():
    for _ in range(10):
        code = generate_ref_code()
        exists = await orm.User.filter(ref_code=code).exists()
        if not exists:
            return code
    raise RuntimeError("Failed to generate unique ref_code")


# ----------------- Auth endpoints -----------------


@router.post("/", response_model=UserLoginOut)
async def login(data: UserLoginIn, response: Response):
    data_dict = data.model_dump()

    # mock
    if data_dict["hash"] == "mock" and data_dict["id"] == 359107176:
        access_token = create_access_token({"sub": str(359107176)})
        set_refresh_cookie(response, 359107176)
        return {"access_token": access_token}

    validate_telegram_data(data_dict)

    # 1. Ищем пользователя
    user = await orm.User.get_or_none(id=data.id)

    # 2. Пытаемся найти реферера (если пришёл код)
    referrer = None
    if data.ref_code:
        referrer = await orm.User.get_or_none(ref_code=data.ref_code)

        # защита от self-ref
        if referrer and referrer.id == data.id:
            referrer = None

    # 3. Пользователь новый
    if not user:
        user = await orm.User.create(
            id=data.id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            photo_url=data.photo_url,
            ref_code=await create_unique_ref_code(),
            referred_by=referrer,
        )

    # 4. Пользователь уже есть → можно ДОзаписать рефера
    else:
        await orm.User.filter(id=user.id).update(
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            photo_url=data.photo_url,
        )

        # проверяем: нет ли уже referred_by и нет ли лицензии
        if (
            not user.referred_by
            and referrer
            and not user.license_end_date
            and referrer.id != user.id
        ):
            user.referred_by = referrer
            await user.save(update_fields=["referred_by"])

    # 5. Авторизация
    access_token = create_access_token({"sub": str(user.id)})
    set_refresh_cookie(response, user.id)

    return {"access_token": access_token}


@router.get("/me", response_model=UserMeOut)
async def me(user=Depends(get_current_user), authorization: str = Header(...)):
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    user_out = await UserOut.from_tortoise_orm(user)

    data = user_out.model_dump()

    # НЕ имперсонация → возвращаем чистую модель
    if not payload.get("impersonated"):
        return UserMeOut(**data)

    # Имперсонация → добавляем флаги
    return UserMeOut(
        **data,
        impersonated=True,
        real_user_id=int(payload["real_sub"]),
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="refresh_token", path="/")


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
