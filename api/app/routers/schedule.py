from datetime import datetime, timedelta, timezone

from aerich import in_transaction
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.common.models import orm
from app.routers.auth import (
    get_current_user,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])


class IntervalOut(BaseModel):
    start: str  # "09:00"
    end: str  # "18:00"


class DayOut(BaseModel):
    weekday: int
    enabled: bool
    intervals: list[IntervalOut]


class ScheduleOut(BaseModel):
    schedule: list[DayOut]


class IntervalIn(BaseModel):
    start: str  # "09:00"
    end: str


class DayIn(BaseModel):
    weekday: int
    enabled: bool
    intervals: list[IntervalIn]


class ScheduleIn(BaseModel):
    schedule: list[DayIn]


@router.get("/working-hours", response_model=ScheduleOut)
async def get_schedule(user=Depends(get_current_user)):
    schedule = (
        await orm.UserWorkDay.filter(user=user)
        .prefetch_related("intervals")
        .order_by("weekday")
    )
    result = []
    for day in schedule:
        intervals = [
            {"start": i.time_from.strftime("%H:%M"), "end": i.time_to.strftime("%H:%M")}
            for i in day.intervals
        ]
        result.append(
            {"weekday": day.weekday, "enabled": day.is_enabled, "intervals": intervals}
        )
    return {"schedule": result}


# ВАЖНО:
# time_from/time_to — локальное время пользователя
# tzinfo используется ТОЛЬКО чтобы удовлетворить Tortoise
# реальная таймзона хранится отдельно (user.timezone)
def local_time_hack(time_str: str):
    # tz пока игнорируется, но оставлен на будущее
    return (
        datetime.strptime(time_str, "%H:%M")
        .time()
        .replace(tzinfo=timezone(timedelta(hours=3)))
    )


@router.post("/working-hours")
async def save_schedule(data: ScheduleIn, user=Depends(get_current_user)):
    async with in_transaction() as conn:  # транзакция на default connection
        for day_data in data.schedule:
            day_obj, _ = await orm.UserWorkDay.get_or_create(
                user=user, weekday=day_data.weekday, using_db=conn
            )
            day_obj.is_enabled = day_data.enabled
            await day_obj.save(update_fields=["is_enabled"], using_db=conn)

            # Удаляем старые интервалы через транзакцию
            await orm.UserWorkInterval.filter(work_day=day_obj).using_db(conn).delete()

            # Создаём новые интервалы
            for interval in day_data.intervals:
                await orm.UserWorkInterval.create(
                    work_day=day_obj,
                    time_from=local_time_hack(interval.start),
                    time_to=local_time_hack(interval.end),
                    using_db=conn,
                )

    return {"status": "ok"}
