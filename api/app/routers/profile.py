from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.routers.auth import get_current_user


class UserTimezone(BaseModel):
    timezone: str

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
            return v
        except ZoneInfoNotFoundError:
            raise ValueError(
                f"Invalid timezone: {v}. "
                f'Must be a valid IANA timezone (e.g., "Europe/Moscow")'
            )


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/timezone")
async def get_timezone(user=Depends(get_current_user)) -> str:
    return user.timezone


@router.post("/timezone")
async def save_timezone(data: UserTimezone, user=Depends(get_current_user)):
    user.timezone = data.timezone
    await user.save(update_feilds=["timezone"])
