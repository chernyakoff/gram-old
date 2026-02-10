from telethon import TelegramClient

from app.common.models import orm
from app.utils.logger import Logger

from .telegram_service import TelegramService


class DialogScanner:
    """Зона ответственности: чтение и поиск данных/сообщений."""

    def __init__(self, client: TelegramClient, telegram: TelegramService, logger: Logger):
        self.client = client
        self.telegram = telegram
        self.logger = logger

    async def ensure_entity(self, recipient: orm.Recipient):
        return await self.telegram.get_entity(recipient)

    async def get_active_dialogs(self, account_id: int) -> list[orm.Dialog]:
        return await orm.Dialog.filter(
            account_id=account_id, finished_at__isnull=True
        ).prefetch_related("recipient", "messages")

    async def get_new_messages_from_telegram(self, dialog: orm.Dialog) -> list:
        """
        Получает новые сообщения от юзера из Telegram.
        Возвращает список новых сообщений (отсортированных по времени).
        """
        peer = await self.telegram.get_peer(dialog.recipient)
        if not peer:
            return []

        last_db_message = (
            await orm.Message.filter(dialog=dialog, ui_only=False)
            .order_by("-created_at")
            .first()
        )

        if not last_db_message or not last_db_message.tg_message_id:
            return []

        new_messages = []
        try:
            async for msg in self.client.iter_messages(
                peer, min_id=last_db_message.tg_message_id
            ):
                if msg.id == last_db_message.tg_message_id:
                    continue
                if msg.out:
                    continue
                new_messages.append(msg)
        except Exception as e:
            if "PeerIdInvalidError" in str(type(e)):
                self.logger.warning(
                    f"[{dialog.recipient.username}] PeerIdInvalid, обновляем entity"
                )
                peer = await self.telegram.get_peer(dialog.recipient)
                if not peer:
                    return []

                try:
                    async for msg in self.client.iter_messages(
                        peer, min_id=last_db_message.tg_message_id
                    ):
                        if msg.id == last_db_message.tg_message_id:
                            continue
                        if msg.out:
                            continue
                        new_messages.append(msg)
                except Exception as retry_error:
                    self.logger.error(
                        f"[{dialog.recipient.username}] Ошибка при повторной попытке: {retry_error}"
                    )
                    return []
            else:
                self.logger.error(
                    f"[{dialog.recipient.username}] Ошибка при получении сообщений: {e}"
                )
                return []

        if new_messages:
            new_messages.sort(key=lambda m: m.date)

        return new_messages

    async def check_old_dialogs_for_new_messages(self, account_id: int) -> list[tuple[orm.Dialog, list]]:
        """
        Возвращает список пар (dialog, new_messages) для диалогов,
        где найдено новое входящее.
        """
        results: list[tuple[orm.Dialog, list]] = []

        dialogs = await orm.Dialog.filter(
            account_id=account_id, finished_at__isnull=True
        ).prefetch_related("recipient", "messages")

        for dialog in dialogs:
            new_messages = await self.get_new_messages_from_telegram(dialog)
            if new_messages:
                results.append((dialog, new_messages))

        return results
