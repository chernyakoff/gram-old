from datetime import datetime

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import InputPeerUser, Message, User

from app.common.models import orm
from app.utils.logger import Logger


class TelegramService:
    client: TelegramClient

    def __init__(self, client: TelegramClient):
        self.client = client

    async def get_peer(self, dialog: orm.Dialog) -> InputPeerUser | None:
        if dialog.recipient_peer_id and dialog.recipient_access_hash:
            return InputPeerUser(
                user_id=dialog.recipient_peer_id,
                access_hash=dialog.recipient_access_hash,
            )
        else:
            entity = await self.client.get_entity(dialog.recipient.username)
            if isinstance(entity, User) and entity.access_hash:
                dialog.recipient_access_hash = entity.access_hash
                dialog.recipient_peer_id = entity.id
                await dialog.save(
                    update_fields=["recipient_access_hash", "recipient_peer_id"]
                )
                return InputPeerUser(
                    user_id=dialog.recipient_peer_id,
                    access_hash=dialog.recipient_access_hash,
                )

    async def get_new_messages(self, peer: InputPeerUser, min_id: int) -> list[Message]:
        messages = []
        async for msg in self.client.iter_messages(peer, min_id=min_id):
            if msg.id == min_id or msg.out:
                continue
            messages.append(msg)
        if messages:
            messages.sort(key=lambda m: m.date)
        return messages


class DialogManager:
    end_time: datetime
    client: TelegramClient
    account: orm.Account
    logger: Logger
    telegram: TelegramService

    recipents: list[orm.Recipient]

    async def continue_dialogs(self):
        dialogs = await orm.Dialog.filter(
            account_id=self.account.id, finished_at__isnull=True
        ).prefetch_related("recipient", "messages")

        self.logger.info(f"Проверка {len(dialogs)} старых диалогов на новые сообщения")

        for dialog in dialogs:
            try:
                peer = await self.telegram.get_peer(dialog)
            except FloodWaitError as e:
                self.logger.info(f"[{self.account.id}] {e}")
                return

            if not peer:
                continue

            last_db_message = (
                await orm.Message.filter(dialog=dialog).order_by("-created_at").first()
            )

            if not last_db_message or not last_db_message.tg_message_id:
                continue

            messages = await self.telegram.get_new_messages(
                peer, last_db_message.tg_message_id
            )

            if messages:
                self.logger.info(
                    f"[{dialog.recipient.username}] Найдено {len(messages)} новых сообщений"
                )
