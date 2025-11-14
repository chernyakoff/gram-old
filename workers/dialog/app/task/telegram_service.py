import asyncio

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
)
from telethon.tl.types import InputPeerUser
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.utils.logger import Logger


class TelegramService:
    """Сервис для работы с Telegram API"""

    def __init__(self, client: TelegramClient, logger: Logger):
        self.client = client
        self.logger = logger

    async def get_entity(self, recipient: orm.Recipient):
        """Получает entity пользователя по username"""
        recipient.attempts += 1
        recipient.last_attempt_at = tz.now()

        try:
            entity = await self.client.get_entity(recipient.username)
            recipient.status = enums.RecipientStatus.PROCESSING
            recipient.last_error = None  # type: ignore
            await recipient.save(
                update_fields=["attempts", "last_attempt_at", "status", "last_error"]
            )
            return entity

        except FloodWaitError as e:
            await self._handle_flood_wait(recipient, e)
            return None

        except (UsernameNotOccupiedError, UsernameInvalidError):
            await self._handle_invalid_username(recipient)
            return None

        except (UserDeactivatedError, UserDeactivatedBanError):
            await self._handle_deactivated_user(recipient)
            return None

        except RPCError as e:
            await self._handle_rpc_error(recipient, e)
            return None

        except Exception as e:
            await self._handle_unexpected_error(recipient, e)
            return None

    async def send_message(
        self, recipient: orm.Recipient, text: str, dialog: orm.Dialog | None = None
    ):
        """Отправляет сообщение получателю"""
        recipient.attempts += 1
        recipient.last_attempt_at = tz.now()
        try:
            # Пытаемся использовать InputPeerUser если есть dialog с данными
            target = recipient.username
            if dialog:
                peer = self._get_peer_from_dialog(dialog)
                if peer:
                    target = peer

            msg = await self.client.send_message(target, text)
            recipient.status = enums.RecipientStatus.SENT
            recipient.last_error = None  # type: ignore
            await recipient.save(
                update_fields=["attempts", "last_attempt_at", "status", "last_error"]
            )
            return msg

        except FloodWaitError as e:
            await self._handle_flood_wait(recipient, e)
            return None

        except SlowModeWaitError as e:
            await self._handle_slow_mode(recipient, e)
            return None

        except ChatWriteForbiddenError:
            await self._handle_chat_forbidden(recipient)
            return None

        except PeerFloodError:
            await self._handle_peer_flood(recipient)
            return None

        except RPCError as e:
            await self._handle_rpc_error(recipient, e)
            return None

        except Exception as e:
            await self._handle_send_error(recipient, e)
            return None

    # === Обработчики ошибок ===

    async def _handle_flood_wait(self, recipient: orm.Recipient, error: FloodWaitError):
        recipient.last_error = f"FloodWait: {error.seconds}s"
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "last_error"]
        )
        self.logger.warning(
            f"[{recipient.username}] FloodWait: ждать {error.seconds} сек"
        )
        await asyncio.sleep(error.seconds)

    async def _handle_slow_mode(
        self, recipient: orm.Recipient, error: SlowModeWaitError
    ):
        recipient.last_error = f"SlowModeWait: {error.seconds}s"
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "last_error"]
        )
        self.logger.warning(
            f"[{recipient.username}] SlowMode {error.seconds}s — ждём..."
        )
        await asyncio.sleep(error.seconds)

    async def _handle_invalid_username(self, recipient: orm.Recipient):
        recipient.last_error = "Username invalid or not occupied"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.warning(f"[{recipient.username}] Username не существует")

    async def _handle_deactivated_user(self, recipient: orm.Recipient):
        recipient.last_error = "User deactivated or banned"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.warning(f"[{recipient.username}] Аккаунт деактивирован")

    async def _handle_chat_forbidden(self, recipient: orm.Recipient):
        recipient.last_error = "Cannot send messages to this chat"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.warning(f"[{recipient.username}] Писать в чат запрещено")

    async def _handle_peer_flood(self, recipient: orm.Recipient):
        recipient.last_error = "PeerFlood: слишком много исходящих"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.error(f"[{recipient.username}] PeerFlood — аккаунт перегружен")

    async def _handle_rpc_error(self, recipient: orm.Recipient, error: RPCError):
        recipient.last_error = f"RPCError: {error.__class__.__name__}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.warning(f"[{recipient.username}] RPCError: {error}")

    async def _handle_unexpected_error(
        self, recipient: orm.Recipient, error: Exception
    ):
        recipient.last_error = f"Unexpected error: {error}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.error(f"[{recipient.username}] Неизвестная ошибка: {error}")

    async def _handle_send_error(self, recipient: orm.Recipient, error: Exception):
        recipient.last_error = f"Unexpected: {error}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        self.logger.error(
            f"[{recipient.username}] Неизвестная ошибка при send_message: {error}"
        )

    def _get_peer_from_dialog(self, dialog: orm.Dialog):
        """Создаёт InputPeerUser из данных диалога если они есть"""
        if dialog.recipient_peer_id and dialog.recipient_access_hash:
            return InputPeerUser(
                user_id=dialog.recipient_peer_id,
                access_hash=dialog.recipient_access_hash,
            )
        return None
