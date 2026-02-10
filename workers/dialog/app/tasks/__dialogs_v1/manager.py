from datetime import datetime

from telethon import TelegramClient

from app.common.models import orm
from app.utils.logger import Logger

from .ai_client import AIClient
from .dialog_ai import DialogAI
from .dialog_delivery import DeliveryService
from .dialog_processor import DialogProcessor
from .dialog_scanner import DialogScanner
from .dialog_scheduler import DialogScheduler
from .reminder_service import ReminderService
from .session_timer import SessionTimer
from .telegram_service import TelegramService


class DialogManager:
    """Фасад над тремя зонами ответственности."""

    def __init__(
        self,
        client: TelegramClient,
        project: orm.Project,
        prompt: dict,
        account: orm.Account,
        logger: Logger,
        stop_event,
    ):
        self.client = client
        self.project = project
        self.prompt = prompt
        self.account = account
        self.logger = logger
        self.stop_event = stop_event

        self.session_timer = SessionTimer(
            initial_minutes=5,
            on_timeout=lambda: self.stop_event.set(),
            logger=self.logger,
        )

        self.ai_client = AIClient(self.account.user, logger)
        self.telegram_service = TelegramService(client, logger)

        self.scanner = DialogScanner(client, self.telegram_service, logger)
        self.dialog_ai = DialogAI(
            self.ai_client,
            self.account,
            self.project,
            self.prompt,
            self.telegram_service,
            self.logger,
        )
        self.delivery = DeliveryService(
            client,
            self.telegram_service,
            self.logger,
            self.session_timer,
        )
        self.reminders = ReminderService(
            self.account,
            self.project,
            self.delivery,
            self.logger,
        )
        self.processor = DialogProcessor(
            account,
            project,
            logger,
            self.dialog_ai,
            self.delivery,
            self.session_timer,
            stop_event,
            self.scanner,
            self.reminders,
        )
        self.scheduler = DialogScheduler(
            client,
            account,
            logger,
            self.session_timer,
            stop_event,
            self.ai_client,
            self.processor,
            self.scanner,
            self.telegram_service,
        )

    async def start_new_dialogs(
        self, recipients_id: list[int], end_time: datetime | None = None
    ) -> int:
        return await self.processor.start_new_dialogs(recipients_id, end_time=end_time)

    async def wait_for_replies(self, end_time):
        await self.scheduler.wait_for_replies(end_time)

    async def check_and_process_dialogs(self) -> tuple[int, int]:
        return await self.processor.check_and_process_dialogs()

    def setup_event_handlers(self):
        self.scheduler.setup_event_handlers()

    async def _monitor_read_receipts(self):
        await self.scheduler.monitor_read_receipts()

    async def check_and_send_reminders(self):
        return await self.processor.check_and_send_reminders()

    async def check_old_dialogs_for_new_messages(self) -> int:
        return await self.processor.check_old_dialogs_for_new_messages()
