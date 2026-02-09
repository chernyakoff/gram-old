from __future__ import annotations

import asyncio
from datetime import datetime

from tortoise import timezone as tz

from app.common.models import orm
from app.common.utils.notify import BotNotify
from app.common.utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    ProjectSkipOptions,
    validate_prompt,
)
from app.utils.logger import Logger

from .manager import DialogManager
from .telegram_service import FrozenError, SpamBlockedError, TelegramService


class DialogFlow:
    """
    Encapsulates dialog business flow:
    - process existing dialogs
    - start new dialogs
    - keep session alive and monitor replies
    """

    def __init__(
        self,
        account: orm.Account,
        telegram: TelegramService,
        logger: Logger,
        stop_event: asyncio.Event,
    ):
        self.account = account
        self.telegram = telegram
        self.logger = logger
        self.stop_event = stop_event
        self.manager: DialogManager | None = None
        self._read_receipts_task: asyncio.Task | None = None

    async def process_existing_dialogs(self) -> tuple[int, int]:
        """
        Process current dialogs and send replies if needed.
        """
        manager = await self._ensure_manager()
        return await manager.check_and_process_dialogs()

    async def start_new_dialogs(
        self, recipients_id: list[int], end_time: datetime | None = None
    ) -> int:
        """
        Start dialogs for recipients.
        """
        manager = await self._ensure_manager()
        return await manager.start_new_dialogs(recipients_id, end_time=end_time)

    async def wait_for_replies(self, end_time: datetime):
        """
        Keep session alive until stop_event or end_time.
        """
        manager = await self._ensure_manager()
        await manager.wait_for_replies(end_time)

    async def shutdown(self):
        if self.manager:
            self.manager.session_timer.cancel()
        if self._read_receipts_task and not self._read_receipts_task.done():
            self._read_receipts_task.cancel()
            try:
                await self._read_receipts_task
            except asyncio.CancelledError:
                pass

    async def _ensure_manager(self) -> DialogManager:
        if self.manager:
            return self.manager

        project = await orm.Project.get(id=self.account.project_id)  # type: ignore
        prompt = await orm.Prompt.get_or_none(project_id=self.account.project_id)  # type: ignore

        if not self.account.premium and project.premium_required:
            premium_error = f"У аккаунта [{self.account.phone}] закончился премиум"
            await BotNotify.warning(self.account.user_id, premium_error)
            raise Exception(premium_error)

        skip_options = (
            ProjectSkipOptions(**project.skip_options)
            if project.skip_options
            else DEFAULT_SKIP_OPTIONS
        )
        if not validate_prompt(prompt, skip_options):
            raise Exception(f"У юзера [{self.account.user_id}] отсутствует промпт")

        if await self.telegram.is_frozen():
            raise FrozenError()

        muted_until = await self.telegram.is_spamblock()
        if muted_until:
            raise SpamBlockedError(muted_until)

        self.manager = DialogManager(
            client=self.telegram.client,  # type: ignore
            project=project,
            prompt=prompt.to_dict() if prompt else {},
            account=self.account,
            logger=self.logger,
            stop_event=self.stop_event,
        )
        self.manager.setup_event_handlers()
        self._read_receipts_task = asyncio.create_task(
            self.manager._monitor_read_receipts()
        )
        return self.manager
