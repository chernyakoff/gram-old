import asyncio
import random
from functools import partial

from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.tl.functions.messages import GetPeerDialogsRequest
from telethon.tl.types import InputDialogPeer
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.utils.logger import Logger

from .ai_client import AIClient
from .dialog_processor import DialogProcessor
from .dialog_scanner import DialogScanner
from .session_timer import SessionTimer
from .telegram_service import TelegramService


WAIT_BEFORE_REPLY_MIN_SEC = 5
WAIT_BEFORE_REPLY_MAX_SEC = 30


async def get_last_active_dialog(username: str, account_id: int) -> orm.Dialog | None:
    dialog = (
        await orm.Dialog.filter(
            recipient__username=username,
            account_id=account_id,
        )
        .exclude(status=enums.DialogStatus.COMPLETE)
        .order_by("-started_at")
        .prefetch_related("recipient")
        .first()
    )
    return dialog


class DialogScheduler:
    """Зона ответственности: таймеры, ожидания, обработчики событий."""

    def __init__(
        self,
        client: TelegramClient,
        account: orm.Account,
        logger: Logger,
        session_timer: SessionTimer,
        stop_event: asyncio.Event,
        ai_client: AIClient,
        processor: DialogProcessor,
        scanner: DialogScanner,
        telegram: TelegramService,
    ):
        self.client = client
        self.account = account
        self.logger = logger
        self.session_timer = session_timer
        self.stop_event = stop_event
        self.ai_client = ai_client
        self.processor = processor
        self.scanner = scanner
        self.telegram = telegram
        self.message_buffers: dict[int, list] = {}
        self._wait_tasks: dict[int, asyncio.Task] = {}

    def setup_event_handlers(self):
        self.client.add_event_handler(
            partial(self._on_new_message),
            NewMessage(),
        )

    async def wait_for_replies(self, end_time):
        self.logger.info(
            f"Account {self.account.id} вошёл в режим ожидания. "
            f"Таймер: {int(self.session_timer.get_remaining_seconds())}с"
        )

        last_check = tz.now()
        CHECK_INTERVAL_SEC = 30

        while tz.now() < end_time and not self.stop_event.is_set():
            if not self.client.is_connected():
                self.logger.error("Потеряно соединение, завершаем задачу")
                return

            if (tz.now() - last_check).total_seconds() >= CHECK_INTERVAL_SEC:
                remaining = int(self.session_timer.get_remaining_seconds())
                self.logger.info(f"⏱️  Таймер: {remaining}с до отключения")
                last_check = tz.now()

            await asyncio.sleep(10)

        if self.stop_event.is_set():
            self.logger.info(
                f"Account {self.account.id} остановлен: "
                f"все диалоги завершены или достигнут лимит"
            )
        else:
            self.logger.info(
                f"Account {self.account.id} остановлен: "
                f"истекло максимальное время сессии"
            )

    async def _on_new_message(self, event: NewMessage.Event):
        try:
            if event.out:
                return

            sender = await event.get_sender()
            if not sender.username:
                return

            text = event.raw_text
            if event.voice:
                oga_bytes = await event.download_media(file=bytes)
                text = await self.ai_client.transcribe(oga_bytes)

            dialog = await get_last_active_dialog(sender.username, self.account.id)
            if not dialog:
                self.logger.info(
                    f"[{sender.username}] Получено новое сообщение, но диалог не найден"
                )
                return

            recipient = dialog.recipient

            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.RECIPIENT,
                tg_message_id=event.id,
                text=text,
            )

            self.logger.info(f"[{recipient.username}] Получено новое сообщение")

            self.session_timer.reset(5)

            if dialog.id not in self.message_buffers:
                self.message_buffers[dialog.id] = []
            self.message_buffers[dialog.id].append(event)

            await self._restart_wait_task(dialog, recipient)

        except Exception as e:
            self.logger.error(f"Ошибка в on_new_message: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    async def _restart_wait_task(self, dialog: orm.Dialog, recipient: orm.Recipient):
        existing = self._wait_tasks.get(dialog.id)
        if existing and not existing.done():
            existing.cancel()

        task = asyncio.create_task(self._wait_and_process_messages(dialog, recipient))
        self._wait_tasks[dialog.id] = task

    async def _wait_and_process_messages(
        self, dialog: orm.Dialog, recipient: orm.Recipient
    ):
        try:
            wait_time = random.randint(
                WAIT_BEFORE_REPLY_MIN_SEC, WAIT_BEFORE_REPLY_MAX_SEC
            )
            self.logger.info(f"[{recipient.username}] Ждём {wait_time}с перед ответом")

            await asyncio.sleep(wait_time)

            events = self.message_buffers.get(dialog.id, [])
            if not events:
                return

            del self.message_buffers[dialog.id]

            self.logger.info(
                f"[{recipient.username}] Обработка {len(events)} накопленных сообщений"
            )

            await self.processor.process_dialog_reply(dialog, recipient, events)

        except asyncio.CancelledError:
            self.logger.info(
                f"[{recipient.username}] Ожидание отменено (пришло новое сообщение)"
            )
        except Exception as e:
            self.logger.error(f"Ошибка в _wait_and_process_messages: {e}")
        finally:
            current = self._wait_tasks.get(dialog.id)
            if current is not None and current.done():
                self._wait_tasks.pop(dialog.id, None)

    async def monitor_read_receipts(self):
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(30)

                try:
                    dialogs = await orm.Dialog.filter(
                        account_id=self.account.id, finished_at__isnull=True
                    ).prefetch_related("recipient")

                    for dialog in dialogs:
                        try:
                            await self._check_read_status_for_dialog(dialog)
                        except Exception as e:
                            self.logger.warning(
                                f"Ошибка при проверке read status для диалога {dialog.id}: {e}"
                            )
                except Exception as e:
                    self.logger.error(f"Ошибка в цикле мониторинга: {e}")

        except asyncio.CancelledError:
            self.logger.info("Мониторинг read receipts остановлен")
        except Exception as e:
            self.logger.error(f"Критическая ошибка в monitor_read_receipts: {e}")

    async def _check_read_status_for_dialog(self, dialog: orm.Dialog):
        peer = await self.telegram.get_peer(dialog.recipient)
        if not peer:
            return

        unread_messages = await orm.Message.filter(
            dialog=dialog,
            sender=enums.MessageSender.ACCOUNT,
            ack=False,
            tg_message_id__isnull=False,
        ).order_by("created_at")

        if not unread_messages:
            return

        try:
            result = await self.client(
                GetPeerDialogsRequest(peers=[InputDialogPeer(peer=peer)])
            )

            if not result.dialogs:  # type: ignore
                return

            dialog_info = result.dialogs[0]  # type: ignore
            read_inbox_max_id = dialog_info.read_inbox_max_id

            updated_count = 0
            for msg in unread_messages:
                if msg.tg_message_id and msg.tg_message_id <= read_inbox_max_id:
                    msg.ack = True
                    await msg.save(update_fields=["ack"])
                    updated_count += 1

            if updated_count > 0:
                self.logger.info(
                    f"[{dialog.recipient.username}] Помечено как прочитанных: {updated_count} сообщений"
                )

        except Exception as e:
            try:
                async for msg in self.client.iter_messages(peer, limit=10):
                    if not msg.out:
                        updated_count = 0
                        for our_msg in unread_messages:
                            if our_msg.tg_message_id and our_msg.tg_message_id < msg.id:
                                our_msg.ack = True
                                await our_msg.save(update_fields=["ack"])
                                updated_count += 1

                        if updated_count > 0:
                            self.logger.warning(
                                f"[{dialog.recipient.username}] Обновлено через fallback: {updated_count}"
                            )
                        break
            except Exception as fallback_error:
                self.logger.warning(
                    f"Не удалось проверить read status для {dialog.id}: {e}, fallback: {fallback_error}"
                )
