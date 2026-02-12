from datetime import datetime, timedelta, timezone

from aerich import in_transaction
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.common.models import orm
from app.routers.auth import get_current_user

router = APIRouter(prefix="/schedule", tags=["schedule"])


class ScheduleMetaOut(BaseModel):
    id: int
    name: str
    timezone: str
    meeting_duration: int
    is_default: bool


class IntervalOut(BaseModel):
    start: str
    end: str


class DayOut(BaseModel):
    weekday: int
    enabled: bool
    intervals: list[IntervalOut]


class ScheduleOut(BaseModel):
    schedule_id: int
    name: str
    schedule: list[DayOut]
    timezone: str
    disabled_month_days: list[int]
    meeting_duration: int
    is_default: bool


class IntervalIn(BaseModel):
    start: str
    end: str


class DayIn(BaseModel):
    weekday: int
    enabled: bool
    intervals: list[IntervalIn]


class ScheduleIn(BaseModel):
    schedule: list[DayIn]


class ScheduleCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    timezone: str = "Europe/Moscow"
    meeting_duration: int = Field(default=30, ge=1, le=24 * 60)


class ScheduleUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    timezone: str | None = None
    meeting_duration: int | None = Field(default=None, ge=1, le=24 * 60)
    is_default: bool | None = None


async def get_user_schedule(user: orm.User, schedule_id: int | None) -> orm.UserSchedule:
    if schedule_id is None:
        return await orm.UserSchedule.get_default_for_user(user)

    schedule = await orm.UserSchedule.get_or_none(id=schedule_id, user_id=user.id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/list", response_model=list[ScheduleMetaOut])
async def list_schedules(user=Depends(get_current_user)):
    schedules = await orm.UserSchedule.filter(user_id=user.id).order_by("id")
    if not schedules:
        schedules = [await orm.UserSchedule.get_default_for_user(user)]

    return [
        {
            "id": s.id,
            "name": s.name,
            "timezone": s.timezone,
            "meeting_duration": s.meeting_duration,
            "is_default": s.is_default,
        }
        for s in schedules
    ]


@router.post("/", response_model=ScheduleMetaOut)
async def create_schedule(data: ScheduleCreateIn, user=Depends(get_current_user)):
    is_first = not await orm.UserSchedule.filter(user_id=user.id).exists()
    schedule = await orm.UserSchedule.create(
        user=user,
        name=data.name,
        timezone=data.timezone,
        meeting_duration=data.meeting_duration,
        is_default=is_first,
    )
    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleMetaOut)
async def update_schedule(
    schedule_id: int, data: ScheduleUpdateIn, user=Depends(get_current_user)
):
    schedule = await get_user_schedule(user, schedule_id)

    update_fields: list[str] = []
    if data.name is not None:
        schedule.name = data.name
        update_fields.append("name")
    if data.timezone is not None:
        schedule.timezone = data.timezone
        update_fields.append("timezone")
    if data.meeting_duration is not None:
        schedule.meeting_duration = data.meeting_duration
        update_fields.append("meeting_duration")

    if data.is_default is True and not schedule.is_default:
        await orm.UserSchedule.filter(user_id=user.id, is_default=True).exclude(
            id=schedule.id
        ).update(is_default=False)
        schedule.is_default = True
        update_fields.append("is_default")

    if update_fields:
        await schedule.save(update_fields=update_fields)
    return schedule


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int, user=Depends(get_current_user)):
    schedule = await get_user_schedule(user, schedule_id)
    schedules_count = await orm.UserSchedule.filter(user_id=user.id).count()

    if schedules_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the last schedule",
        )

    async with in_transaction() as conn:
        new_default_id: int | None = None
        if schedule.is_default:
            replacement = (
                await orm.UserSchedule.filter(user_id=user.id)
                .exclude(id=schedule.id)
                .order_by("id")
                .using_db(conn)
                .first()
            )
            if not replacement:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete the last schedule",
                )

            replacement.is_default = True
            await replacement.save(update_fields=["is_default"], using_db=conn)
            new_default_id = replacement.id

        await schedule.delete(using_db=conn)

    return {
        "status": "ok",
        "deleted_id": schedule_id,
        "new_default_id": new_default_id,
    }


@router.get("/", response_model=ScheduleOut)
async def get_schedule(
    schedule_id: int | None = Query(default=None),
    user=Depends(get_current_user),
):
    schedule_obj = await get_user_schedule(user, schedule_id)
    schedule = (
        await orm.UserWorkDay.filter(schedule_id=schedule_obj.id)
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

    days = await (
        orm.UserDisabledMonthDay.filter(schedule_id=schedule_obj.id)
        .order_by("day")
        .values_list("day", flat=True)
    )

    return {
        "schedule_id": schedule_obj.id,
        "name": schedule_obj.name,
        "schedule": result,
        "timezone": schedule_obj.timezone,
        "meeting_duration": schedule_obj.meeting_duration,
        "disabled_month_days": list(days),
        "is_default": schedule_obj.is_default,
    }


def local_time_hack(time_str: str):
    return (
        datetime.strptime(time_str, "%H:%M")
        .time()
        .replace(tzinfo=timezone(timedelta(hours=3)))
    )


@router.post("/working-hours")
async def save_schedule(
    data: ScheduleIn,
    schedule_id: int | None = Query(default=None),
    user=Depends(get_current_user),
):
    schedule_obj = await get_user_schedule(user, schedule_id)

    async with in_transaction() as conn:
        for day_data in data.schedule:
            day_obj, _ = await orm.UserWorkDay.get_or_create(
                schedule_id=schedule_obj.id,
                weekday=day_data.weekday,
                using_db=conn,
            )
            day_obj.is_enabled = day_data.enabled
            await day_obj.save(update_fields=["is_enabled"], using_db=conn)

            await orm.UserWorkInterval.filter(work_day=day_obj).using_db(conn).delete()

            for interval in day_data.intervals:
                await orm.UserWorkInterval.create(
                    work_day=day_obj,
                    time_from=local_time_hack(interval.start),
                    time_to=local_time_hack(interval.end),
                    using_db=conn,
                )

    return {"status": "ok"}


class ToggleDayIn(BaseModel):
    day: int = Field(ge=1, le=31)


@router.post("/toggle-day")
async def toggle_day(
    data: ToggleDayIn,
    schedule_id: int | None = Query(default=None),
    user=Depends(get_current_user),
):
    schedule_obj = await get_user_schedule(user, schedule_id)
    obj = await orm.UserDisabledMonthDay.get_or_none(
        schedule_id=schedule_obj.id,
        day=data.day,
    )

    if obj:
        await obj.delete()
        return {
            "day": data.day,
            "disabled": False,
        }

    await orm.UserDisabledMonthDay.create(
        schedule_id=schedule_obj.id,
        day=data.day,
    )

    return {
        "day": data.day,
        "disabled": True,
    }
