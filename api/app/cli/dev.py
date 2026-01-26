from datetime import datetime, timedelta
from typing import List

from cyclopts import App
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models.enums import WeekDay
from app.common.models.orm import Dialog, Meeting, User

app = App(name="dev", help="dev tests etc")


class TimeSlot:
    def __init__(self, start: datetime, end: datetime):
        if start >= end:
            raise ValueError("Start must be before end")
        self.start = start
        self.end = end

    def __str__(self):
        # Например: "29 Jan 2026, 10:15 - 11:15"
        return (
            f"{self.start.strftime('%d %b %Y, %H:%M')} - {self.end.strftime('%H:%M')}"
        )

    def duration(self):
        return self.end - self.start

    def to_tuple(self):
        return self.start, self.end

    def overlaps(self, other: "TimeSlot"):
        return self.start < other.end and self.end > other.start

    def __lt__(self, other: "TimeSlot"):
        return self.start < other.start

    def __eq__(self, other: "TimeSlot"):
        return self.start == other.start and self.end == other.end


class ScheduleService:
    def __init__(self, user: User):
        self.user = user
        self.meeting_duration = timedelta(minutes=self.user.meeting_duration)

    async def get_available_slots(self, days_ahead: int = 7) -> List[TimeSlot]:
        available_slots: List[TimeSlot] = []

        today = tz.now().date()

        for day_offset in range(days_ahead):
            current_date = today + timedelta(days=day_offset)

            # 1. Проверяем, не выключен ли день
            disabled = await self.user.disabled_month_days.filter(
                day=current_date.day
            ).exists()
            if disabled:
                continue

            # 2. Получаем рабочий день
            weekday_enum = WeekDay(current_date.weekday() + 1)
            work_day = (
                await self.user.work_days.filter(weekday=weekday_enum, is_enabled=True)
                .prefetch_related("intervals")
                .first()
            )
            if not work_day:
                continue

            # 3. Преобразуем рабочие интервалы в datetime
            work_intervals = [
                (
                    datetime.combine(current_date, interval.time_from),
                    datetime.combine(current_date, interval.time_to),
                )
                for interval in work_day.intervals
            ]
            if not work_intervals:
                continue

            # 4. Получаем занятые интервалы (уже назначенные встречи)
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)

            busy_intervals = [
                (meeting.start_at, meeting.end_at)
                for meeting in await self.user.meetings.filter(  # type: ignore
                    start_at__gte=day_start,
                    start_at__lt=day_end,
                    status="scheduled",  # учитываем только активные встречи
                ).all()
            ]

            # 5. Вычитаем busy из work_intervals
            free_intervals = self._subtract_intervals(work_intervals, busy_intervals)

            # 6. Нарезаем по meeting_duration и шагу
            slots = self._split_by_duration(free_intervals)
            available_slots.extend(slots)

        return available_slots

    def _subtract_intervals(self, free, busy):
        """Вычитает busy интервалы из free"""
        result = []

        for f_start, f_end in free:
            cursor = f_start
            for b_start, b_end in sorted(busy):
                if b_end <= cursor or b_start >= f_end:
                    continue
                if b_start > cursor:
                    result.append((cursor, b_start))
                cursor = max(cursor, b_end)
            if cursor < f_end:
                result.append((cursor, f_end))

        return result

    def _split_by_duration(self, intervals) -> List[TimeSlot]:
        """
        Разбивает интервалы на TimeSlot объекты без пересечений.
        self.meeting_duration — шаг между слотами (и длина слота).
        """
        slots: List[TimeSlot] = []

        for start, end in intervals:
            cursor = start
            while cursor + self.meeting_duration <= end:
                slots.append(TimeSlot(cursor, cursor + self.meeting_duration))
                cursor += (
                    self.meeting_duration
                )  # следующий слот начинается сразу после этого

        return slots


async def book_meeting(
    user, dialog, slot_start: datetime, slot_end: datetime, source="auto"
):
    """
    Создаёт встречу для пользователя на выбранный слот и связывает с диалогом.
    Проверяет пересечения, чтобы слот был свободен.

    :param user: User instance
    :param dialog: Dialog instance
    :param slot_start: datetime начала встречи
    :param slot_end: datetime конца встречи
    :param source: источник создания (manual/api/auto)
    :return: Meeting instance
    """

    async with in_transaction():
        # Проверяем, нет ли пересечения с другими встречами
        overlapping = (
            await Meeting.filter(
                user=user,
                start_at__lt=slot_end,
                end_at__gt=slot_start,
                status="scheduled",  # учитываем только активные встречи
            )
            .select_for_update()
            .exists()
        )

        if overlapping:
            raise ValueError("Слот занят, выберите другой")

        # Создаём встречу
        meeting = await Meeting.create(
            user=user,
            dialog=dialog,  # связь с диалогом
            start_at=slot_start,
            end_at=slot_end,
            status="scheduled",
            source=source,
        )

        # Обновляем диалог, если нужно (у тебя OneToOne, Tortoise делает это автоматически)
        # dialog.meeting = meeting
        # await dialog.save()

        return meeting


@app.default
async def _():
    user = await User.get(id=359107176)
    service = ScheduleService(user)
    slots = await service.get_available_slots(days_ahead=2)

    chosen_slot = slots[-1]
    dialog = await Dialog.get(id=2367)
    meeting = await book_meeting(user, dialog, chosen_slot.start, chosen_slot.end)
