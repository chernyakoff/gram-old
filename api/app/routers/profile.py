from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.common.models import orm
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


class MeetingDuration(BaseModel):
    value: int


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/timezone")
async def get_timezone(user=Depends(get_current_user)) -> str:
    schedule = await orm.UserSchedule.get_default_for_user(user)
    return schedule.timezone


@router.post("/timezone")
async def save_timezone(data: UserTimezone, user=Depends(get_current_user)):
    schedule = await orm.UserSchedule.get_default_for_user(user)
    schedule.timezone = data.timezone
    await schedule.save(update_fields=["timezone"])


@router.post("/meeting-duration")
async def save_meeting_duration(data: MeetingDuration, user=Depends(get_current_user)):
    schedule = await orm.UserSchedule.get_default_for_user(user)
    schedule.meeting_duration = data.value
    await schedule.save(update_fields=["meeting_duration"])
