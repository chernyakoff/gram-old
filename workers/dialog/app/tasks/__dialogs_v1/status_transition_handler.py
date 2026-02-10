from app.common.models import enums, orm
from app.utils.logger import Logger

from .telegram_service import TelegramService


class StatusTransitionHandler:
    """Side-effects for status transitions (files, notifications, etc.)."""

    def __init__(self, telegram: TelegramService, logger: Logger):
        self.telegram = telegram
        self.logger = logger

    async def handle_status_change(
        self,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        project: orm.Project,
        old_status: enums.DialogStatus,
        new_status: enums.DialogStatus,
    ):
        if new_status == old_status:
            return

        files = await orm.ProjectFile.filter(
            project_id=project.id, status=new_status
        ).all()
        if not files:
            return

        for f in files:
            msg = await self.telegram.send_file(recipient, f)
            if msg:
                await orm.Message.create(
                    dialog=dialog,
                    tg_message_id=msg.id,  # type: ignore
                    sender=enums.MessageSender.ACCOUNT,
                    text=f"{f.filename}\n{f.title}",
                    ui_only=True,
                )
