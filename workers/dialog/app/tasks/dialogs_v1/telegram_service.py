import asyncio
import re
from datetime import datetime
from io import BytesIO

from telethon import TelegramClient
from telethon.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    PeerFloodError,
    RPCError,
    SlowModeWaitError,
    UserDeactivatedBanError,
    UserDeactivatedError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
    YouBlockedUserError,
)
from telethon.tl.functions.contacts import UnblockRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import InputPeerUser, User
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.common.utils.s3 import AsyncS3Client
from app.utils.logger import Logger


class SpamBlockedError(Exception):
    def __init__(self, muted_until: datetime):
        self.muted_until = muted_until
        super().__init__(f"Account is muted until {muted_until}")


class FrozenError(Exception):
    pass


class TelegramService:
    """Сервис для работы с Telegram API"""

    def __init__(self, client: TelegramClient, logger: Logger):
        self.client = client
        self.logger = logger

    def _touch_recipient(self, recipient: orm.Recipient):
        recipient.attempts += 1
        recipient.last_attempt_at = tz.now()

    async def get_entity(self, recipient: orm.Recipient):
        """Получает entity пользователя по username"""
        self._touch_recipient(recipient)

        try:
            entity = await self.client.get_entity(recipient.username)
            recipient.last_error = None  # type: ignore
            if isinstance(entity, User):
                recipient.peer_id = entity.id
                if isinstance(entity.access_hash, int):
                    recipient.access_hash = entity.access_hash
                if isinstance(entity.first_name, str):
                    recipient.first_name = entity.first_name
                if isinstance(entity.last_name, str):
                    recipient.last_name = entity.last_name
                if isinstance(entity.premium, bool):
                    recipient.premium = entity.premium
                info = await self.get_recipient_info(entity)
                if info:
                    recipient.about = info["about"]
                    recipient.channel = info["channel"]

            await recipient.save()
            return entity

        except Exception as e:
            await self._handle_error(recipient, e, phase="get_entity")
            return None

    async def get_peer(self, recipient: orm.Recipient):
        """
        Возвращает InputPeerUser, при необходимости сначала получает entity.
        """
        if not (recipient.peer_id and recipient.access_hash):
            await self.get_entity(recipient)

        if recipient.peer_id and recipient.access_hash:
            return InputPeerUser(
                user_id=recipient.peer_id,
                access_hash=recipient.access_hash,
            )
        return None

    async def send_message(self, recipient: orm.Recipient, text: str):
        """Отправляет сообщение получателю"""
        self._touch_recipient(recipient)
        try:
            peer = await self.get_peer(recipient)
            if not peer:
                raise Exception("PeerId and AccessHash not found")

            msg = await self.client.send_message(peer, text)
            recipient.status = enums.RecipientStatus.SENT
            recipient.last_error = None  # type: ignore
            await recipient.save(
                update_fields=["attempts", "last_attempt_at", "status", "last_error"]
            )
            return msg

        except Exception as e:
            await self._handle_error(recipient, e, phase="send_message")
            return None

    # === Обработчики ошибок ===


    async def is_frozen(self, username: str = "Telegram", timeout: float = 5.0) -> bool:
        try:
            await asyncio.wait_for(self.client.get_entity(username), timeout=timeout)
            return False
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            self.logger.warning(f"Не удалось проверить frozen status: {e}")
            return True

    async def is_spamblock(self) -> datetime | None:
        try:
            await self.client.send_message("spambot", "/start")
        except YouBlockedUserError:
            await self.client(UnblockRequest("spambot"))  # type: ignore
            await asyncio.sleep(0.5)
            await self.client.send_message("spambot", "/start")

        await asyncio.sleep(1)

        messages = await self.client.get_messages("spambot", limit=1)
        if not messages:
            return

        if isinstance(messages, list):
            text = messages[0].message
        else:
            text = messages.message
        if len(text) < 120:
            return
        forever = datetime.now().replace(year=datetime.now().year + 10)
        matches = re.search(r"\d+\s\w+\s\d+,\s\d+:\d+\s\w+", text)
        if matches:
            try:
                return datetime.strptime(matches[0], "%d %b %Y, %H:%M %Z")
            except:
                return forever
        else:
            return forever

    async def get_recipient_info(self, entity) -> dict | None:
        """Получает about и channel для конкретного entity"""
        params = {}
        try:
            response = await self.client(GetFullUserRequest(entity))
            params["about"] = response.full_user.about  # type: ignore
            params["channel"] = (
                response.chats[0].username if response.chats else None  # type: ignore
            )
            return params
        except:
            return None

    async def send_file(self, recipient: orm.Recipient, file: orm.ProjectFile):
        self._touch_recipient(recipient)
        try:
            peer = await self.get_peer(recipient)
            if not peer:
                raise Exception("PeerId and AccessHash not found")

            async with AsyncS3Client() as s3:  # type: ignore
                content_bytes = await s3.get(file.storage_path)

            buffer = BytesIO(content_bytes)
            buffer.name = file.filename

            msg = await self.client.send_file(peer, buffer, caption=file.title)

            return msg
        except Exception as e:
            await self._handle_error(recipient, e, phase="send_file")
            return None

    async def _update_recipient_error(
        self,
        recipient: orm.Recipient,
        error: str,
        status: enums.RecipientStatus | None = None,
    ):
        recipient.last_error = error
        if status is not None:
            recipient.status = status
            update_fields = ["attempts", "last_attempt_at", "status", "last_error"]
        else:
            update_fields = ["attempts", "last_attempt_at", "last_error"]
        await recipient.save(update_fields=update_fields)

    async def _handle_error(
        self,
        recipient: orm.Recipient,
        error: Exception,
        phase: str,
    ):
        if isinstance(error, FloodWaitError):
            await self._update_recipient_error(
                recipient, f"FloodWait: {error.seconds}s"
            )
            self.logger.warning(
                f"[{recipient.username}] FloodWait ({phase}): ждать {error.seconds} сек"
            )
            # await asyncio.sleep(error.seconds)
            return

        if isinstance(error, SlowModeWaitError):
            await self._update_recipient_error(
                recipient, f"SlowModeWait: {error.seconds}s"
            )
            self.logger.warning(
                f"[{recipient.username}] SlowMode ({phase}) {error.seconds}s — ждём..."
            )
            await asyncio.sleep(error.seconds)
            return

        error_map = {
            (UsernameNotOccupiedError, UsernameInvalidError): (
                "Username invalid or not occupied",
                enums.RecipientStatus.FAILED,
                "warning",
                "Username не существует",
            ),
            (UserDeactivatedError, UserDeactivatedBanError): (
                "User deactivated or banned",
                enums.RecipientStatus.FAILED,
                "warning",
                "Аккаунт деактивирован",
            ),
            (ChatWriteForbiddenError,): (
                "Cannot send messages to this chat",
                enums.RecipientStatus.FAILED,
                "warning",
                "Писать в чат запрещено",
            ),
            (PeerFloodError,): (
                "PeerFlood: слишком много исходящих",
                enums.RecipientStatus.FAILED,
                "error",
                "PeerFlood — аккаунт перегружен",
            ),
            (RPCError,): (
                None,
                enums.RecipientStatus.FAILED,
                "warning",
                "RPCError",
            ),
        }

        for exc_types, (msg, status, level, log_msg) in error_map.items():
            if isinstance(error, exc_types):
                if msg is None:
                    msg = f"RPCError: {error.__class__.__name__}"
                await self._update_recipient_error(
                    recipient,
                    msg,
                    status=status,
                )
                if log_msg == "RPCError":
                    self.logger.warning(
                        f"[{recipient.username}] RPCError ({phase}): {error}"
                    )
                else:
                    getattr(self.logger, level)(
                        f"[{recipient.username}] {log_msg}"
                    )
                return

        await self._update_recipient_error(
            recipient,
            f"Unexpected: {error}",
            status=enums.RecipientStatus.FAILED,
        )
        self.logger.error(
            f"[{recipient.username}] Неизвестная ошибка ({phase}): {error}"
        )
