import asyncio

from app.common.models import enums, orm
from app.common.utils.prompt import get_name_addon
from app.utils.logger import Logger

from .ai_client import AIClient
from .status_resolver import StatusResolver
from .status_transition_handler import StatusTransitionHandler
from .telegram_service import TelegramService


class DialogAI:
    """AI pipeline: status resolve + response generation."""

    def __init__(
        self,
        ai_client: AIClient,
        account: orm.Account,
        project: orm.Project,
        prompt: dict,
        telegram: TelegramService,
        logger: Logger,
    ):
        self.ai_client = ai_client
        self.account = account
        self.project = project
        self.prompt = prompt
        self.telegram = telegram
        self.logger = logger

        self.status_resolver = StatusResolver(account.user, logger)
        self.status_transition = StatusTransitionHandler(telegram, logger)

    async def get_reply(
        self,
        dialog: orm.Dialog,
        messages: list[orm.Message],
        recipient: orm.Recipient,
        timeout_sec: int = 60,
    ) -> tuple[str | None, enums.DialogStatus | None, bool]:
        old_status = dialog.status
        status = await self.status_resolver.resolve_status(
            messages,
            self.project,
            old_status,
        )

        if status != old_status:
            await self.status_transition.handle_status_change(
                dialog,
                recipient,
                self.project,
                old_status,
                status,
            )

        if status in [
            enums.DialogStatus.COMPLETE,
            enums.DialogStatus.NEGATIVE,
            enums.DialogStatus.OPERATOR,
        ]:
            return None, status, True

        name_addon = get_name_addon(self.account, recipient)

        response = await asyncio.wait_for(
            self.ai_client.generate_response(
                self.prompt, status, dialog, messages, name_addon, self.project
            ),
            timeout=timeout_sec,
        )

        if response == "COMPLETE":
            return "COMPLETE", enums.DialogStatus.COMPLETE, False

        return response, status, False
