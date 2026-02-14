# Pydantic модель для базовой информации о пользователе
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from models.orm import User
from api.routers.auth import get_current_user

router = APIRouter(prefix="/partners", tags=["partners"])


class UserBasicOut(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None


# Pydantic модель для партнёров с ссылкой на пригласившего и рефералов
class PartnerOut(UserBasicOut):
    referred_by: Optional[UserBasicOut] = None
    referrals: list[UserBasicOut] = []


@router.get("/", response_model=PartnerOut)
async def get_partners(user: User = Depends(get_current_user)):
    # Загружаем пользователя с его пригласившим и рефералами
    await user.fetch_related("referred_by", "referrals")

    # Конвертация в Pydantic вручную
    def to_basic(u: User) -> UserBasicOut:
        return UserBasicOut(
            id=u.id,
            username=u.username,
            first_name=u.first_name,
            last_name=u.last_name,
            photo_url=u.photo_url,
        )

    result = PartnerOut(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        photo_url=user.photo_url,
        referred_by=to_basic(user.referred_by) if user.referred_by else None,
        referrals=[to_basic(u) for u in user.referrals],  # type: ignore
    )
    return result
