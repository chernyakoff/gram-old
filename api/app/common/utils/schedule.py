from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import List

from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models.enums import WeekDay
from app.common.models.orm import Dialog, Meeting, User


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

    async def get_available_slots(
        self, date: str, days_ahead: int = 7
    ) -> List[TimeSlot]:
        available_slots: List[TimeSlot] = []

        try:
            start_date: date_cls = date_cls.fromisoformat(date)
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")

        today = tz.now().date()
        if start_date < today:
            start_date = today

        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)

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


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_slots",
            "description": "Получить доступные временные слоты начиная с указанной даты",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Дата начала в формате YYYY-MM-DD",
                    }
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Забронировать выбранный временной слот",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_key": {
                        "type": "string",
                        "description": "Ключ слота, полученный из get_slots",
                    }
                },
                "required": ["slot_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_meeting",
            "description": "Отменить текущую встречу",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],  # пустой список
            },
        },
    },
]


class ToolContext:
    def __init__(self, user: User, dialog: Dialog | None, days_ahead=3):
        self.dialog = dialog
        self.user = user
        self.days_ahead = days_ahead

    async def _get_meeting(self) -> Meeting | None:
        if not self.dialog:
            return None
        return await Meeting.get_or_none(dialog_id=self.dialog.id)

    def _parse_slot_key(self, slot_key: str) -> TimeSlot:
        start_s, end_s = slot_key.split("__")
        return TimeSlot(
            start=datetime.fromisoformat(start_s),
            end=datetime.fromisoformat(end_s),
        )

    def _slot_to_dict(self, slot: TimeSlot) -> dict:
        return {
            "slot_key": f"{slot.start.isoformat()}__{slot.end.isoformat()}",
            "start": slot.start.isoformat(),
            "end": slot.end.isoformat(),
        }

    async def get_slots(self, date: str):
        service = ScheduleService(self.user)
        slots = await service.get_available_slots(date=date, days_ahead=self.days_ahead)
        return {"slots": [self._slot_to_dict(s) for s in slots]}

    async def book_slot(self, slot_key: str):
        slot = self._parse_slot_key(slot_key)

        if not self.dialog:
            return {
                "status": "ok",
                "message": "Тестовый режим: встреча не была создана",
                "start": slot.start.isoformat(),
                "end": slot.end.isoformat(),
            }

        meeting = await book_meeting(
            user=self.user,
            dialog=self.dialog,
            slot_start=slot.start,
            slot_end=slot.end,
            source="auto",
        )

        return {
            "meeting_id": meeting.id,
            "start": meeting.start_at.isoformat(),
            "end": meeting.end_at.isoformat(),
        }

    async def cancel_meeting(self):
        meeting = await self._get_meeting()
        if not meeting:
            return {"status": "error", "message": "Встреча не найдена"}

        await meeting.delete()
        return {"status": "ok", "message": "Встреча отменена"}
