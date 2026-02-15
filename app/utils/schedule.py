from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo

from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from models.orm import Dialog, Meeting, User, UserSchedule, WeekDay


class TimeSlot:
    def __init__(self, start: datetime, end: datetime, schedule_id: int | None = None):
        if start >= end:
            raise ValueError("Start must be before end")
        self.start = start
        self.end = end
        self.schedule_id = schedule_id

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
    def __init__(self, user: User, schedule: UserSchedule | None = None):
        self.user = user
        self.schedule = schedule

    async def get_available_slots(
        self, date: str, days_ahead: int = 7
    ) -> List[TimeSlot]:
        try:
            start_date: date_cls = date_cls.fromisoformat(date)
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")

        # We do not allow scheduling "today". The minimum date is "tomorrow"
        # in the schedule timezone, but we may have multiple schedules, so we
        # enforce per-schedule in _get_available_slots_for_schedule too.
        today_utc = tz.now().date()
        if start_date < today_utc:
            start_date = today_utc

        schedules: list[UserSchedule]
        if self.schedule:
            schedules = [self.schedule]
        else:
            schedules = await UserSchedule.filter(user_id=self.user.id).order_by("id")
            if not schedules:
                schedules = [await UserSchedule.get_default_for_user(self.user)]

        available_slots: List[TimeSlot] = []
        for schedule in schedules:
            schedule_slots = await self._get_available_slots_for_schedule(
                schedule=schedule,
                start_date=start_date,
                days_ahead=days_ahead,
            )
            available_slots.extend(schedule_slots)

        return sorted(available_slots)

    async def _get_available_slots_for_schedule(
        self, schedule: UserSchedule, start_date: date_cls, days_ahead: int
    ) -> List[TimeSlot]:
        available_slots: List[TimeSlot] = []
        meeting_duration = timedelta(minutes=schedule.meeting_duration)

        # Disallow "today" in schedule timezone.
        try:
            local_today = tz.now().astimezone(ZoneInfo(schedule.timezone)).date()
        except Exception:
            local_today = tz.now().date()
        min_date = local_today + timedelta(days=1)
        if start_date < min_date:
            start_date = min_date

        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)

            # 1. Проверяем, не выключен ли день
            disabled = await schedule.disabled_month_days.filter(
                day=current_date.day
            ).exists()
            if disabled:
                continue

            # 2. Получаем рабочий день
            weekday_enum = WeekDay(current_date.weekday() + 1)
            work_day = (
                await schedule.work_days.filter(weekday=weekday_enum, is_enabled=True)
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
                for meeting in await schedule.meetings.filter(  # type: ignore
                    start_at__gte=day_start,
                    start_at__lt=day_end,
                    status="scheduled",
                ).all()
            ]

            # 5. Вычитаем busy из work_intervals
            free_intervals = self._subtract_intervals(work_intervals, busy_intervals)

            # 6. Нарезаем по meeting_duration и шагу
            slots = self._split_by_duration(
                free_intervals,
                meeting_duration=meeting_duration,
                schedule_id=schedule.id,
            )
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

    def _split_by_duration(
        self,
        intervals,
        meeting_duration: timedelta,
        schedule_id: int,
    ) -> List[TimeSlot]:
        """
        Разбивает интервалы на TimeSlot объекты без пересечений.
        meeting_duration — шаг между слотами (и длина слота).
        """
        slots: List[TimeSlot] = []

        for start, end in intervals:
            cursor = start
            while cursor + meeting_duration <= end:
                slots.append(
                    TimeSlot(
                        cursor,
                        cursor + meeting_duration,
                        schedule_id=schedule_id,
                    )
                )
                cursor += (
                    meeting_duration  # следующий слот начинается сразу после этого
                )

        return slots


async def book_meeting(
    user,
    dialog,
    slot_start: datetime,
    slot_end: datetime,
    source="auto",
    schedule: UserSchedule | None = None,
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
    schedule = schedule or await UserSchedule.get_default_for_user(user)

    # Hard guardrail: never allow meetings on "today" in schedule timezone.
    # NOTE: our slots are naive datetimes (no tzinfo), so we compare by date.
    try:
        local_today = tz.now().astimezone(ZoneInfo(schedule.timezone)).date()
    except Exception:
        local_today = tz.now().date()
    if slot_start.date() <= local_today:
        raise ValueError("Нельзя назначить встречу на сегодня")

    async with in_transaction():
        # Проверяем, нет ли пересечения с другими встречами
        overlapping = (
            await Meeting.filter(
                user=user,
                schedule=schedule,
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
            schedule=schedule,
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
                    },
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
        # In-memory guardrail within a single tool loop: we only allow booking
        # slot_keys that were actually returned by get_slots in this request.
        self._last_slot_keys: set[str] = set()

    # Best-effort state for the prompt test UI where dialog is None and we don't
    # persist meetings. This avoids repeated "booking" tool calls across turns.
    _test_booked_by_user: dict[int, str] = {}

    @classmethod
    def reset_test_state(cls, user_id: int) -> None:
        cls._test_booked_by_user.pop(user_id, None)

    async def _get_schedule(self, schedule_id: int | None = None) -> UserSchedule:
        if schedule_id is None:
            return await UserSchedule.get_default_for_user(self.user)

        schedule = await UserSchedule.get_or_none(id=schedule_id, user_id=self.user.id)
        if not schedule:
            raise ValueError("Расписание не найдено")
        return schedule

    async def _get_meeting(self) -> Meeting | None:
        if not self.dialog:
            return None
        return await Meeting.get_or_none(dialog_id=self.dialog.id)

    def _slot_to_dict(self, slot: TimeSlot) -> dict:
        if slot.schedule_id is None:
            raise ValueError("Отсутствует schedule_id у слота")

        return {
            "slot_key": (
                f"{slot.schedule_id}__{slot.start.isoformat()}__{slot.end.isoformat()}"
            ),
            "start": slot.start.isoformat(),
            "end": slot.end.isoformat(),
            "schedule_id": slot.schedule_id,
        }

    async def get_slots(self, date: str, schedule_id: int | None = None):
        # schedule_id is intentionally kept optional in the handler signature for
        # backward compatibility, but we do not encourage the model to pass it
        # (it is frequently hallucinated). If it is invalid, return an error
        # payload rather than failing the whole AI response.
        schedule = None
        if schedule_id:
            try:
                schedule = await self._get_schedule(schedule_id)
            except Exception as e:
                return {"status": "error", "message": str(e), "slots": []}
        service = ScheduleService(self.user, schedule)
        slots = await service.get_available_slots(date=date, days_ahead=self.days_ahead)
        payload_slots = [self._slot_to_dict(s) for s in slots]
        self._last_slot_keys = {s["slot_key"] for s in payload_slots}
        payload: dict = {"slots": payload_slots}

        # Hint for the model in the test UI: a prior slot might already be "booked".
        if not self.dialog:
            booked = self._test_booked_by_user.get(self.user.id)
            if booked:
                payload["already_booked_slot_key"] = booked
        return payload

    async def book_slot(self, slot_key: str):
        if self._last_slot_keys and slot_key not in self._last_slot_keys:
            return {
                "status": "error",
                "message": "slot_key не найден среди доступных слотов; сначала вызови get_slots и используй slot_key из ответа",
            }

        # If this dialog already has a scheduled meeting, make booking idempotent.
        if self.dialog:
            existing = await Meeting.get_or_none(
                dialog_id=self.dialog.id, status="scheduled"
            )
            if existing:
                if existing.start_at and existing.end_at:
                    existing_key = f"{existing.schedule_id}__{existing.start_at.isoformat()}__{existing.end_at.isoformat()}"
                    if slot_key == existing_key:
                        return {
                            "status": "ok",
                            "message": "Слот уже забронирован ранее",
                            "meeting_id": existing.id,
                            "start": existing.start_at.isoformat(),
                            "end": existing.end_at.isoformat(),
                        }
                return {
                    "status": "error",
                    "message": "Встреча уже забронирована; если нужно изменить время, сначала вызови cancel_meeting, затем выбери новый слот",
                    "meeting_id": existing.id,
                    "start": existing.start_at.isoformat()
                    if existing.start_at
                    else None,
                    "end": existing.end_at.isoformat() if existing.end_at else None,
                }

        parsed = slot_key.split("__", 2)
        if len(parsed) != 3:
            raise ValueError("Некорректный slot_key")

        schedule_id_str, start_s, end_s = parsed
        slot = TimeSlot(
            start=datetime.fromisoformat(start_s),
            end=datetime.fromisoformat(end_s),
        )
        try:
            schedule = await self._get_schedule(int(schedule_id_str))
        except Exception as e:
            return {"status": "error", "message": str(e)}

        if not self.dialog:
            prev = self._test_booked_by_user.get(self.user.id)
            if prev == slot_key:
                return {
                    "status": "ok",
                    "message": "Тестовый режим: слот уже был выбран ранее",
                    "start": slot.start.isoformat(),
                    "end": slot.end.isoformat(),
                }
            self._test_booked_by_user[self.user.id] = slot_key
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
            schedule=schedule,
        )

        return {
            "meeting_id": meeting.id,
            "start": meeting.start_at.isoformat(),
            "end": meeting.end_at.isoformat(),
        }

    async def cancel_meeting(self):
        # Test chat mode: there is no persisted Meeting; clear in-memory selection.
        if not self.dialog:
            existed = self._test_booked_by_user.pop(self.user.id, None)
            if not existed:
                return {"status": "error", "message": "Встреча не найдена"}
            return {"status": "ok", "message": "Встреча отменена"}

        meeting = await self._get_meeting()
        if not meeting:
            return {"status": "error", "message": "Встреча не найдена"}

        await meeting.delete()
        return {"status": "ok", "message": "Встреча отменена"}
