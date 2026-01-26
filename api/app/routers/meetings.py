from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.common.models import orm
from app.routers.auth import (
    get_current_user,
)

router = APIRouter(prefix="/meetings", tags=["meetings"])


class DayMeeting(BaseModel):
    date: date
    count: int


@router.get("/", response_model=list[DayMeeting])
async def get_meetings(
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    user: orm.User = Depends(get_current_user),
) -> list[DayMeeting]:
    """
    Возвращает для указанного месяца количество встреч на каждый день (только SCHEDULED).
    """
    # Диапазон дат месяца
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # Получаем все встречи пользователя на месяц со статусом SCHEDULED
    meetings = await orm.Meeting.filter(
        user_id=user.id,
        status=orm.MeetingStatus.SCHEDULED,
        start_at__gte=start_date,
        start_at__lt=end_date,
    ).values("start_at")

    # Группируем по дню
    counts: dict[date, int] = defaultdict(int)
    for m in meetings:
        day = m["start_at"].date()
        counts[day] += 1

    # Формируем результат
    result = [
        DayMeeting(date=day, count=count) for day, count in sorted(counts.items())
    ]
    return result


class MeetingOut(BaseModel):
    id: int
    start_at: datetime
    end_at: datetime
    username: str
    dialog_id: int


@router.get(
    "/day",
    response_model=list[MeetingOut],
)
async def load_day_meetings(
    date_: date = Query(..., alias="date"),
    user: orm.User = Depends(get_current_user),
):
    """
    Возвращает список встреч пользователя за конкретный день
    """

    start_dt = datetime.combine(date_, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    meetings = (
        await orm.Meeting.filter(
            user_id=user.id,
            status=orm.MeetingStatus.SCHEDULED,
            start_at__gte=start_dt,
            start_at__lt=end_dt,
        )
        .select_related("dialog__recipient")
        .order_by("start_at")
    )

    result: list[MeetingOut] = []

    for m in meetings:
        recipient = m.dialog.recipient if m.dialog else None

        result.append(
            MeetingOut(
                id=m.id,
                start_at=m.start_at,
                end_at=m.end_at,
                username=recipient.username if recipient else "",
                dialog_id=m.dialog_id,  # type: ignore
            )
        )

    return result
