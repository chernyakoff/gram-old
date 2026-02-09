import asyncio
import random
from datetime import datetime, timedelta

import pytz
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.utils.logger import Logger

from .dialog_delivery import DeliveryService


class ReminderService:
    """Handles reminders (morning and meeting)."""

    def __init__(
        self,
        account: orm.Account,
        project: orm.Project,
        delivery: DeliveryService,
        logger: Logger,
    ):
        self.account = account
        self.project = project
        self.delivery = delivery
        self.logger = logger

    async def check_and_send_reminders(self):
        try:
            morning_sent = await self._check_morning_reminders()
            meeting_sent = await self._check_meeting_reminders()

            total = morning_sent + meeting_sent

            if total > 0:
                self.logger.info(
                    f"📧 Отправлено напоминаний: "
                    f"утренних={morning_sent}, о встречах={meeting_sent}"
                )

            return total

        except Exception as e:
            self.logger.error(f"Ошибка при проверке напоминаний: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return 0

    def _get_user_now(self) -> datetime:
        user_tz = pytz.timezone(self.account.user.timezone or "Europe/Moscow")
        return datetime.now(user_tz)

    def _is_morning_time(self, user_now: datetime) -> bool:
        current_hour = user_now.hour
        current_minute = user_now.minute

        target_hour = self.project.send_time_start

        current_minutes = current_hour * 60 + current_minute
        target_minutes = target_hour * 60

        diff = abs(current_minutes - target_minutes)

        return diff <= 30

    async def _send_reminder_immediately(
        self, dialog: orm.Dialog, reminder_text: str
    ) -> bool:
        try:
            recipient = dialog.recipient

            msg = await self.delivery.send_plain(recipient, reminder_text)

            if not msg:
                self.logger.error(
                    f"[{recipient.username}] Не удалось отправить напоминание"
                )
                return False

            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=reminder_text,
            )

            self.logger.info(
                f"[{recipient.username}] ✅ Напоминание отправлено: {reminder_text[:50]}..."
            )

            return True

        except Exception as e:
            self.logger.error(
                f"[{recipient.username}] Ошибка отправки напоминания: {e}"
            )
            return False

    async def _check_morning_reminders(self):
        if not self.project.use_calendar or not self.project.morning_reminder:
            return 0

        user_now = self._get_user_now()
        today = user_now.date()

        if not self._is_morning_time(user_now):
            return 0

        meetings = await orm.Meeting.filter(
            dialog__account_id=self.account.id,
            start_at__date=today,
            status=orm.MeetingStatus.SCHEDULED,
        ).prefetch_related("dialog__recipient")

        sent_count = 0

        for meeting in meetings:
            already_sent = await orm.MorningReminderSent.exists(meeting=meeting)
            if already_sent:
                continue

            dialog = meeting.dialog
            if dialog.project_id != self.project.id:
                continue

            success = await self._send_reminder_immediately(
                dialog, self.project.morning_reminder
            )

            if success:
                dialog.status = enums.DialogStatus.CLOSING
                await dialog.save(update_fields=["status"])
                await orm.MorningReminderSent.create(meeting=meeting)
                sent_count += 1

                await asyncio.sleep(random.randint(3, 7))

        return sent_count

    async def _check_meeting_reminders(self):
        if not self.project.use_calendar or not self.project.meeting_reminder:
            return 0

        now = tz.now()

        hour_from_now_min = now + timedelta(minutes=45)
        hour_from_now_max = now + timedelta(minutes=75)

        meetings = await orm.Meeting.filter(
            dialog__account_id=self.account.id,
            start_at__gte=hour_from_now_min,
            start_at__lte=hour_from_now_max,
            status=orm.MeetingStatus.SCHEDULED,
        ).prefetch_related("dialog__recipient")

        sent_count = 0

        for meeting in meetings:
            already_sent = await orm.MeetingReminderSent.exists(meeting=meeting)
            if already_sent:
                continue

            dialog = meeting.dialog
            if dialog.project_id != self.project.id:
                continue

            reminder_text = self._format_meeting_reminder(
                self.project.meeting_reminder, meeting
            )

            success = await self._send_reminder_immediately(dialog, reminder_text)

            if success:
                dialog.status = enums.DialogStatus.CLOSING
                await dialog.save(update_fields=["status"])
                await orm.MeetingReminderSent.create(meeting=meeting)
                sent_count += 1

                await asyncio.sleep(random.randint(3, 7))

        return sent_count

    def _format_meeting_reminder(self, template: str, meeting: orm.Meeting) -> str:
        user_tz = pytz.timezone(self.account.user.timezone or "Europe/Moscow")
        meeting_time = meeting.start_at.astimezone(user_tz)

        return template.format(
            time=meeting_time.strftime("%H:%M"),
            TIME=meeting_time.strftime("%H:%M"),
            date=meeting_time.strftime("%d.%m.%Y"),
            DATE=meeting_time.strftime("%d.%m.%Y"),
            datetime=meeting_time.strftime("%d.%m.%Y %H:%M"),
            DATETIME=meeting_time.strftime("%d.%m.%Y %H:%M"),
        )
