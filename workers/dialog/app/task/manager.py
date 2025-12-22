import asyncio
import random
from datetime import timedelta
from functools import partial

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.events import NewMessage
from telethon.tl.functions.messages import GetPeerDialogsRequest
from telethon.tl.types import InputDialogPeer
from telethon.types import User as TelethonUser
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.common.utils.notify import BotNotify, notify_complete_dialog
from app.common.utils.prompt import get_name_addon
from app.utils.logger import Logger

from .ai_service import AIService
from .telegram_service import TelegramService

# Константы
WAIT_FOR_REPLY_MINUTES = 5
WAIT_BEFORE_REPLY_MIN_SEC = 30
WAIT_BEFORE_REPLY_MAX_SEC = 60


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


class DialogManager:
    """Менеджер диалогов - координирует работу с диалогами"""

    def __init__(
        self,
        client: TelegramClient,
        project: orm.Project,
        prompt: dict,
        account: orm.Account,
        logger: Logger,
        stop_event: asyncio.Event,
    ):
        self.client = client
        self.project = project
        self.prompt = prompt
        self.account = account
        self.logger = logger
        self.stop_event = stop_event

        self.ai_service = AIService(self.account.user)
        self.telegram_service = TelegramService(client, logger)

        # Отслеживаем диалоги текущей сессии
        self.session_recipients_ids: set[int] = set()
        self.session_start_time = tz.now()

        # Для отслеживания ожидания ответов
        self.waiting_dialogs: dict[int, asyncio.Task] = {}  # dialog_id -> waiting task

        # Буфер для накопления сообщений
        self.message_buffers: dict[int, list] = {}  # dialog_id -> list of messages

        # Счетчик активных диалогов (тех, что ждут ответа)
        self.active_dialogs_count = 0

        # НОВОЕ: Отслеживание диалогов в процессе обработки (генерация AI-ответа)
        self.processing_replies: set[int] = set()  # dialog_ids в обработке
        self.monitor_task: asyncio.Task | None = None

    async def check_and_process_dialogs(self) -> tuple[int, int]:
        """
        Проверяет диалоги в правильном порядке:
        1. Отправляет system-сообщения
        2. Получает новые сообщения от юзеров
        3. Генерирует AI-ответы с учётом ВСЕГО контекста

        Возвращает: (dialogs_with_system, dialogs_with_replies)
        """
        dialogs = await orm.Dialog.filter(
            account_id=self.account.id, finished_at__isnull=True
        ).prefetch_related("recipient", "messages")

        dialogs_with_system = 0
        dialogs_with_replies = 0

        for dialog in dialogs:
            try:
                # ШАГ 1: Проверяем и отправляем system-сообщения
                has_system = await self._process_system_messages_for_dialog(dialog)
                if has_system:
                    dialogs_with_system += 1
                    await asyncio.sleep(random.randint(5, 10))

                # ШАГ 2: Проверяем новые сообщения от юзера в Telegram
                new_messages = await self._get_new_messages_from_telegram(dialog)

                if not new_messages:
                    # Если нет новых - но были system, запускаем ожидание
                    if has_system:
                        asyncio.create_task(
                            self.start_waiting_for_first_reply(dialog, dialog.recipient)
                        )
                    continue

                # ШАГ 3: Сохраняем новые сообщения в БД
                for msg in new_messages:
                    await orm.Message.create(
                        dialog=dialog,
                        sender=enums.MessageSender.RECIPIENT,
                        tg_message_id=msg.id,
                        text=msg.text or "",
                    )

                dialogs_with_replies += 1

                # ШАГ 4: Генерируем AI-ответ с учётом ВСЕХ сообщений
                await self._process_dialog_reply(dialog, dialog.recipient, new_messages)

            except FloodWaitError:
                self.logger.warning("FloodWait при обработке диалогов - прерываем")
                return dialogs_with_system, dialogs_with_replies
            except Exception as e:
                self.logger.error(f"Ошибка при обработке диалога {dialog.id}: {e}")
                import traceback

                self.logger.error(traceback.format_exc())
                continue

        return dialogs_with_system, dialogs_with_replies

    async def _process_system_messages_for_dialog(self, dialog: orm.Dialog) -> bool:
        """
        Проверяет и отправляет system-сообщения для конкретного диалога.
        Возвращает True если были отправлены system-сообщения.
        """
        messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

        if not messages:
            return False

        # Ищем неотправленные system-сообщения в конце
        system_messages = []
        for msg in reversed(messages):
            if msg.sender == enums.MessageSender.SYSTEM and msg.tg_message_id is None:
                system_messages.insert(0, msg)
            elif (
                msg.sender == enums.MessageSender.SYSTEM
                and msg.tg_message_id is not None
            ):
                # Встретили отправленное system - продолжаем искать
                continue
            else:
                # Встретили не-system - прерываем
                break

        if not system_messages:
            return False

        # НОВОЕ: Если есть system-сообщения, переводим диалог в статус MANUAL
        if dialog.status != enums.DialogStatus.MANUAL:
            self.logger.info(
                f"[{dialog.recipient.username}] Обнаружены SYSTEM сообщения, "
                f"переключение в режим MANUAL (было: {dialog.status.value})"
            )
            dialog.status = enums.DialogStatus.MANUAL
            await dialog.save(update_fields=["status"])

        # Отправляем все накопленные system-сообщения
        for sys_msg in system_messages:
            try:
                msg = await self.telegram_service.send_message(
                    dialog.recipient, sys_msg.text
                )

                if msg:
                    sys_msg.tg_message_id = msg.id
                    await sys_msg.save(update_fields=["tg_message_id"])

                    self.logger.info(
                        f"[{dialog.recipient.username}] Отправлено MANUAL system: {sys_msg.text[:50]}"
                    )

                    await asyncio.sleep(random.randint(2, 5))
            except Exception as e:
                self.logger.error(f"Ошибка отправки system-сообщения {sys_msg.id}: {e}")
                # Не прерываем, пытаемся отправить следующее
                continue

        return True

    async def _get_new_messages_from_telegram(self, dialog: orm.Dialog) -> list:
        """
        Получает новые сообщения от юзера из Telegram.
        Возвращает список новых сообщений (отсортированных по времени).
        """
        peer = self.telegram_service._get_peer(dialog.recipient)
        if not peer:
            await self.telegram_service.get_entity(dialog.recipient)
            peer = self.telegram_service._get_peer(dialog.recipient)
            if not peer:
                return []

        # Получаем последнее сообщение из БД
        last_db_message = (
            await orm.Message.filter(dialog=dialog).order_by("-created_at").first()
        )

        if not last_db_message or not last_db_message.tg_message_id:
            return []

        # Получаем новые сообщения из Telegram
        new_messages = []
        async for msg in self.client.iter_messages(
            peer, min_id=last_db_message.tg_message_id
        ):
            if msg.id == last_db_message.tg_message_id:
                continue
            if msg.out:  # Пропускаем исходящие
                continue
            new_messages.append(msg)

        if new_messages:
            new_messages.sort(key=lambda m: m.date)

        return new_messages

    def register_session_recipient(self, recipient_id: int):
        """Регистрирует recipient как часть текущей сессии"""
        self.session_recipients_ids.add(recipient_id)

    async def start_waiting_for_first_reply(
        self, dialog: orm.Dialog, recipient: orm.Recipient
    ):
        """Запускает ожидание ответа на первое сообщение"""
        self.active_dialogs_count += 1
        try:
            await self._wait_for_reply(dialog, recipient)
        finally:
            self.active_dialogs_count = max(0, self.active_dialogs_count - 1)

    def setup_event_handlers(self):
        """Регистрирует обработчики событий"""
        self.client.add_event_handler(
            partial(self._on_new_message),
            NewMessage(),
        )
        self.monitor_task = asyncio.create_task(self._monitor_read_receipts())

    async def _monitor_read_receipts(self):
        """Периодически проверяет статус прочитанных сообщений"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд

                try:
                    # Получаем все активные диалоги
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
            self.logger.error(f"Критическая ошибка в _monitor_read_receipts: {e}")

    async def _check_read_status_for_dialog(self, dialog: orm.Dialog):
        """Проверяет и обновляет статус прочтения сообщений в диалоге"""

        # Получаем peer для диалога
        peer = self.telegram_service._get_peer(dialog.recipient)
        if not peer:
            await self.telegram_service.get_entity(dialog.recipient)
            peer = self.telegram_service._get_peer(dialog.recipient)
            if not peer:
                return

        # Получаем непрочитанные сообщения от аккаунта (наши сообщения)
        unread_messages = await orm.Message.filter(
            dialog=dialog,
            sender=enums.MessageSender.ACCOUNT,
            ack=False,
            tg_message_id__isnull=False,
        ).order_by("created_at")

        if not unread_messages:
            return

        try:
            # Получаем информацию о диалоге из Telegram
            result = await self.client(
                GetPeerDialogsRequest(peers=[InputDialogPeer(peer=peer)])
            )

            if not result.dialogs:  # type: ignore
                return

            dialog_info = result.dialogs[0]  # type: ignore
            read_inbox_max_id = dialog_info.read_inbox_max_id

            # Обновляем статус прочитанных сообщений
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
            # Fallback: используем альтернативный метод
            try:
                # Получаем последнее входящее сообщение и проверяем его ID
                async for msg in self.client.iter_messages(peer, limit=10):
                    if not msg.out:  # Входящее сообщение
                        # Все наши сообщения с ID <= ID последнего входящего считаем прочитанными
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

    async def check_old_dialogs_for_new_messages(self) -> int:
        """
        Проверяет старые незавершенные диалоги на новые сообщения.
        Возвращает количество диалогов, в которых найдены новые сообщения.
        """
        dialogs_with_messages = 0

        try:
            # Получаем все незавершенные диалоги для этого аккаунта
            dialogs = await orm.Dialog.filter(
                account_id=self.account.id, finished_at__isnull=True
            ).prefetch_related("recipient", "messages")

            self.logger.info(
                f"Проверка {len(dialogs)} старых диалогов на новые сообщения"
            )

            for dialog in dialogs:
                try:
                    peer = self.telegram_service._get_peer(dialog.recipient)
                    if not peer:
                        await self.telegram_service.get_entity(dialog.recipient)
                        peer = self.telegram_service._get_peer(dialog.recipient)
                        if not peer:
                            continue

                    # Получаем последнее сообщение из БД
                    last_db_message = (
                        await orm.Message.filter(dialog=dialog)
                        .order_by("-created_at")
                        .first()
                    )

                    if not last_db_message or not last_db_message.tg_message_id:
                        continue

                    # Получаем новые сообщения из Telegram
                    new_messages = []
                    async for msg in self.client.iter_messages(
                        peer, min_id=last_db_message.tg_message_id
                    ):
                        # Пропускаем само последнее сообщение
                        if msg.id == last_db_message.tg_message_id:
                            continue
                        # Пропускаем исходящие (наши) сообщения
                        if msg.out:
                            continue
                        new_messages.append(msg)

                    if new_messages:
                        # Сортируем по времени (от старых к новым)
                        new_messages.sort(key=lambda m: m.date)

                        self.logger.info(
                            f"[{dialog.recipient.username}] Найдено {len(new_messages)} новых сообщений"
                        )

                        # Сохраняем все новые сообщения в БД
                        for msg in new_messages:
                            await orm.Message.create(
                                dialog=dialog,
                                sender=enums.MessageSender.RECIPIENT,
                                tg_message_id=msg.id,
                                text=msg.text or "",
                            )

                        # Отвечаем на новые сообщения
                        await self._process_dialog_reply(
                            dialog, dialog.recipient, new_messages
                        )
                        dialogs_with_messages += 1

                except FloodWaitError:
                    return 0

                except Exception as e:
                    self.logger.error(f"Ошибка при проверке диалога {dialog.id}: {e}")
                    continue

            return dialogs_with_messages

        except Exception as e:
            self.logger.error(f"Ошибка при проверке старых диалогов: {e}")
            return 0

    async def _on_new_message(self, event: NewMessage.Event):
        """Обработчик входящих сообщений"""
        try:
            # Пропускаем исходящие сообщения
            if event.out:
                return

            sender = await event.get_sender()
            if not sender.username:
                return

            text = event.raw_text
            if event.voice:
                oga_bytes = await event.download_media(file=bytes)
                text = await self.ai_service.transcribe(oga_bytes)

            # Находим диалог
            dialog = await get_last_active_dialog(sender.username, self.account.id)
            if not dialog:
                self.logger.info(
                    f"[{sender.username}] Получено новое сообщение, но диалог не найден"
                )
                return

            recipient = dialog.recipient

            # Сохраняем сообщение от получателя
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.RECIPIENT,
                tg_message_id=event.id,
                text=text,
            )

            self.logger.info(f"[{recipient.username}] Получено новое сообщение")

            # Если уже есть задача ожидания для этого диалога - отменяем её

            if dialog.id in self.waiting_dialogs:
                self.waiting_dialogs[dialog.id].cancel()
                del self.waiting_dialogs[dialog.id]

            # Добавляем сообщение в буфер
            if dialog.id not in self.message_buffers:
                self.message_buffers[dialog.id] = []
            self.message_buffers[dialog.id].append(event)

            # Создаём задачу ожидания дополнительных сообщений
            wait_task = asyncio.create_task(
                self._wait_and_process_messages(dialog, recipient)
            )
            self.waiting_dialogs[dialog.id] = wait_task

        except Exception as e:
            self.logger.error(f"Ошибка в on_new_message: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    async def _wait_and_process_messages(
        self, dialog: orm.Dialog, recipient: orm.Recipient
    ):
        """Ждёт 30-60 секунд, затем обрабатывает накопленные сообщения"""
        try:
            wait_time = random.randint(
                WAIT_BEFORE_REPLY_MIN_SEC, WAIT_BEFORE_REPLY_MAX_SEC
            )
            self.logger.info(f"[{recipient.username}] Ждём {wait_time}с перед ответом")

            await asyncio.sleep(wait_time)

            # Получаем накопленные сообщения
            events = self.message_buffers.get(dialog.id, [])
            if not events:
                return

            # Очищаем буфер
            del self.message_buffers[dialog.id]

            self.logger.info(
                f"[{recipient.username}] Обработка {len(events)} накопленных сообщений"
            )

            # Обрабатываем диалог
            await self._process_dialog_reply(dialog, recipient, events)

        except asyncio.CancelledError:
            self.logger.info(
                f"[{recipient.username}] Ожидание отменено (пришло новое сообщение)"
            )
        except Exception as e:
            self.logger.error(f"Ошибка в _wait_and_process_messages: {e}")
        finally:
            # Удаляем задачу из словаря
            if dialog.id in self.waiting_dialogs:
                del self.waiting_dialogs[dialog.id]

    async def _process_dialog_reply(
        self, dialog: orm.Dialog, recipient: orm.Recipient, events: list
    ):
        """Обрабатывает диалог и отправляет ответ"""
        # НОВОЕ: Помечаем что этот диалог в обработке
        self.processing_replies.add(dialog.id)

        try:
            # Проверяем лимит сообщений
            messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

            if len(messages) >= self.project.dialog_limit:
                await self._close_dialog(dialog, recipient, "лимит сообщений")
                return

            if await self._check_spam_messages(messages, recipient):
                await self._close_dialog(dialog, recipient, "спам одинаковых сообщений")
                self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
                return

            # НОВОЕ: Если диалог в статусе MANUAL - не генерируем AI ответ
            if dialog.status == enums.DialogStatus.MANUAL:
                self.logger.info(
                    f"[{recipient.username}] Диалог в режиме MANUAL, "
                    f"ожидаем SYSTEM сообщения от оператора"
                )
                # Запускаем ожидание следующего ответа
                await self._wait_for_reply(dialog, recipient)
                return

            # ИЗМЕНЕНО: Получаем булевый результат - продолжать ли диалог
            should_continue = await self._generate_and_send_response(
                events[0], dialog, recipient, messages
            )

            # НОВОЕ: Только если диалог не завершён - запускаем ожидание
            if should_continue:
                await self._wait_for_reply(dialog, recipient)
            else:
                self.logger.info(
                    f"[{recipient.username}] Диалог завершён, пропускаем ожидание ответа"
                )

        except Exception as e:
            self.logger.error(f"Ошибка в _process_dialog_reply: {e}")
        finally:
            # НОВОЕ: Убираем пометку что диалог в обработке
            self.processing_replies.discard(dialog.id)

    async def _wait_for_reply(self, dialog: orm.Dialog, recipient: orm.Recipient):
        """Ждёт ответа в течение WAIT_FOR_REPLY_MINUTES минут"""
        try:
            wait_until = tz.now() + timedelta(minutes=WAIT_FOR_REPLY_MINUTES)
            self.logger.info(
                f"[{recipient.username}] Ожидание ответа {WAIT_FOR_REPLY_MINUTES} минут"
            )

            while tz.now() < wait_until:
                # Проверяем, не пришло ли новое сообщение
                if dialog.id in self.message_buffers:
                    self.logger.info(
                        f"[{recipient.username}] Получен ответ, продолжаем диалог"
                    )
                    return

                # Проверяем, не остановлена ли задача
                if self.stop_event.is_set():
                    return

                await asyncio.sleep(5)  # Проверяем каждые 5 секунд

            # Если не дождались ответа - закрываем диалог
            self.logger.info(
                f"[{recipient.username}] Не получен ответ за {WAIT_FOR_REPLY_MINUTES} минут, останавливаем диалог"
            )
            await self._close_dialog(dialog, recipient, "нет ответа")

        except Exception as e:
            self.logger.error(f"Ошибка в _wait_for_reply: {e}")

    async def _generate_and_send_response(
        self,
        event,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
    ) -> bool:
        """
        Генерирует ответ от AI и отправляет его.

        Returns:
            bool: True если нужно продолжить ожидание ответа,
                False если диалог завершён
        """

        fresh_messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

        # Ищем неотправленные system-сообщения в конце
        unsent_system = []
        for msg in reversed(fresh_messages):
            if msg.sender == enums.MessageSender.SYSTEM and msg.tg_message_id is None:
                unsent_system.insert(0, msg)
            else:
                break

        # Если есть - отправляем ДО генерации AI-ответа
        if unsent_system:
            self.logger.info(
                f"[{recipient.username}] Обнаружены новые system-сообщения, переход в MANUAL режим"
            )

            # НОВОЕ: Переводим в MANUAL режим
            if dialog.status != enums.DialogStatus.MANUAL:
                self.logger.info(
                    f"[{recipient.username}] Переключение в режим MANUAL из-за system-сообщений"
                )
                dialog.status = enums.DialogStatus.MANUAL
                await dialog.save(update_fields=["status"])

            for sys_msg in unsent_system:
                msg = await self.telegram_service.send_message(recipient, sys_msg.text)
                if msg:
                    sys_msg.tg_message_id = msg.id
                    await sys_msg.save(update_fields=["tg_message_id"])
                    await asyncio.sleep(random.randint(2, 5))

            # НОВОЕ: Если режим MANUAL - не генерируем AI ответ, возвращаемся
            self.logger.info(
                f"[{recipient.username}] Режим MANUAL активен, пропускаем AI генерацию"
            )
            # ВАЖНО: Возвращаем True, т.к. диалог продолжается в MANUAL режиме
            return True

        # НОВОЕ: Дополнительная проверка статуса перед генерацией
        if dialog.status == enums.DialogStatus.MANUAL:
            self.logger.info(
                f"[{recipient.username}] Диалог в MANUAL режиме, AI ответ не генерируется"
            )
            # ВАЖНО: Возвращаем True, т.к. диалог продолжается в MANUAL режиме
            return True

        # Далее идет существующий код генерации AI ответа
        MAX_RETRIES = 3

        name_addon = get_name_addon(self.account, recipient)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ai_response, new_status = await asyncio.wait_for(
                    self.ai_service.get_response_with_status(
                        self.prompt,
                        dialog.status,
                        messages,
                        name_addon,
                        self.logger,
                    ),
                    timeout=60,
                )

                if not ai_response:
                    self.logger.warning(
                        f"[{recipient.username}] AI не вернул ответ (attempt {attempt})"
                    )
                    if attempt == MAX_RETRIES:
                        # Останавливаем диалог при критической ошибке AI
                        await self._close_dialog(dialog, recipient, "AI error")
                        # ВАЖНО: Уменьшаем счётчик
                        self.active_dialogs_count = max(
                            0, self.active_dialogs_count - 1
                        )
                        # ВАЖНО: Возвращаем False = диалог завершён
                        return False
                    else:
                        await asyncio.sleep(2)
                        continue

                break

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"[{recipient.username}] OpenAI timeout (attempt {attempt})"
                )
                if attempt == MAX_RETRIES:
                    # Останавливаем диалог при критической ошибке AI
                    await self._close_dialog(dialog, recipient, "AI timeout")
                    # ВАЖНО: Уменьшаем счётчик
                    self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
                    # ВАЖНО: Возвращаем False = диалог завершён
                    return False
                else:
                    await asyncio.sleep(2)

        if not ai_response:
            # ВАЖНО: Возвращаем False = диалог завершён
            return False

        if new_status == enums.DialogStatus.CLOSING:
            asyncio.create_task(notify_complete_dialog(dialog, self.account))  # type: ignore

        # Обновляем статус диалога
        await self._update_dialog_status(dialog, recipient, new_status, messages)

        # Если AI вернул COMPLETE - диалог завершён
        if ai_response == "COMPLETE":
            self.logger.info(f"[{recipient.username}] AI завершил диалог (COMPLETE)")
            asyncio.create_task(notify_complete_dialog(dialog, self.account))  # type: ignore
            # ВАЖНО: Уменьшаем счётчик активных диалогов
            self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
            # ВАЖНО: Возвращаем False = НЕ продолжаем ожидание
            return False

        # НОВОЕ: Проверяем терминальный статус NEGATIVE
        if dialog.status == enums.DialogStatus.NEGATIVE:
            self.logger.info(
                f"[{recipient.username}] AI установил статус NEGATIVE - диалог завершён"
            )
            # ВАЖНО: Уменьшаем счётчик активных диалогов
            self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
            # ВАЖНО: Возвращаем False = НЕ продолжаем ожидание
            return False

        # НОВОЕ: Проверяем терминальный статус OPERATOR
        if dialog.status == enums.DialogStatus.OPERATOR:
            self.logger.info(
                f"[{recipient.username}] AI установил статус OPERATOR - требуется оператор"
            )
            asyncio.create_task(
                BotNotify.warning(
                    self.account.user_id, f"@{recipient.username} требует оператора"
                )
            )
            # ВАЖНО: Уменьшаем счётчик активных диалогов
            self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
            # ВАЖНО: Возвращаем False = НЕ продолжаем ожидание
            return False

        # Отправляем read acknowledge
        await asyncio.sleep(random.randint(3, 10))
        await self.client.send_read_acknowledge(event.chat_id)

        # Показываем "печатает..."
        async with self.client.action(event.chat_id, "typing"):  # type: ignore
            await asyncio.sleep(random.randint(10, 20))
            msg = await self.telegram_service.send_message(recipient, ai_response)

        if msg:
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=ai_response,
            )
            self.logger.info(f"[{recipient.username}] Отправлен ответ")

        # ВАЖНО: Возвращаем True = продолжаем ожидание ответа
        return True

    async def _update_dialog_status(
        self,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        new_status: enums.DialogStatus | None,
        messages: list[orm.Message],
    ):
        """
        Обновляет статус диалога на основе ответа AI.
        ВАЖНО: Только AI может менять статусы диалогов!
        """

        if new_status and new_status != dialog.status:
            old_status = dialog.status
            dialog.status = new_status

            # Только AI может установить статус COMPLETE
            if new_status in [
                enums.DialogStatus.COMPLETE,
                enums.DialogStatus.NEGATIVE,
                enums.DialogStatus.OPERATOR,
            ]:
                dialog.finished_at = tz.now()

            await dialog.save()
            self.logger.info(
                f"[{recipient.username}] AI изменил статус: {old_status.value} -> {new_status.value}"
            )

        elif not new_status:
            # Эвристика: если 2+ сообщений от пользователя
            recipient_messages = [
                m for m in messages if m.sender == enums.MessageSender.RECIPIENT
            ]
            if (
                len(recipient_messages) >= 2
                and dialog.status == enums.DialogStatus.INIT
            ):
                dialog.status = enums.DialogStatus.ENGAGE
                await dialog.save()
                self.logger.info(
                    f"[{recipient.username}] Автоматически установлен статус ENGAGE"
                )

    async def _close_dialog(
        self, dialog: orm.Dialog, recipient: orm.Recipient, reason: str
    ):
        """Закрывает диалог без изменения статуса (статус меняет только AI)"""

        self.logger.info(f"[{recipient.username}] Диалог остановлен: {reason}")

        # Отменяем задачу ожидания если она есть
        if dialog.id in self.waiting_dialogs:
            self.waiting_dialogs[dialog.id].cancel()
            del self.waiting_dialogs[dialog.id]

        # Очищаем буфер сообщений
        if dialog.id in self.message_buffers:
            del self.message_buffers[dialog.id]

    async def _check_and_stop_if_needed(self):
        """Проверяет условия для остановки task"""

        # 1. Если нет диалогов в сессии - завершаемся
        if not self.session_recipients_ids:
            self.logger.info("🛑 Нет диалогов в текущей сессии")
            self.stop_event.set()
            return

        # 2. Считаем незавершенные диалоги сессии
        total_session_dialogs = len(self.session_recipients_ids)

        # НОВОЕ: Расширенное логирование состояния
        self.logger.info(
            f"[Аккаунт {self.account.id}] Состояние: "
            f"всего_в_сессии={total_session_dialogs}, "
            f"ожидают_ответа={self.active_dialogs_count}, "
            f"в_обработке={len(self.processing_replies)}, "
            f"waiting_tasks={len(self.waiting_dialogs)}, "
            f"buffered={len(self.message_buffers)}"
        )

        # 3. КЛЮЧЕВАЯ ПРОВЕРКА: учитываем и active_dialogs_count и processing_replies
        if (
            self.active_dialogs_count == 0
            and len(self.processing_replies) == 0
            and total_session_dialogs > 0
        ):
            self.logger.info(
                f"🛑 Все диалоги завершены "
                f"(активных={self.active_dialogs_count}, "
                f"в_обработке={len(self.processing_replies)})"
            )
            self.stop_event.set()
            return

        # 4. Проверяем дневной лимит для аккаунта (только для логирования)
        counter = await orm.AccountActionCounter.filter(
            account=self.account,
            action=enums.AccountAction.NEW_DIALOG,
            date=tz.now().date(),
        ).first()

        dialogs_today = counter.count if counter else 0

        if dialogs_today >= self.account.out_daily_limit:
            self.logger.info(
                f"ℹ️ Дневной лимит достигнут: {dialogs_today}/{self.account.out_daily_limit}. "
                f"Активных: {self.active_dialogs_count}, в обработке: {len(self.processing_replies)}. "
                f"Завершим после их окончания."
            )

    async def _check_spam_messages(
        self, messages: list[orm.Message], recipient: orm.Recipient, threshold: int = 3
    ) -> bool:
        """
        Проверяет, отправляет ли пользователь одинаковые сообщения.

        Args:
            messages: Список всех сообщений диалога
            recipient: Получатель
            threshold: Количество одинаковых сообщений подряд для закрытия (по умолчанию 3)

        Returns:
            True если обнаружен спам, False иначе
        """
        # Фильтруем только сообщения от получателя
        recipient_messages = [
            m for m in messages if m.sender == enums.MessageSender.RECIPIENT
        ]

        if len(recipient_messages) < threshold:
            return False

        # Берем последние N сообщений
        recent_messages = recipient_messages[-threshold:]

        # Нормализуем текст (убираем пробелы, приводим к нижнему регистру)
        normalized_texts = [
            m.text.strip().lower() if m.text else "" for m in recent_messages
        ]

        # Проверяем, все ли тексты одинаковые
        if len(set(normalized_texts)) == 1 and normalized_texts[0]:
            self.logger.warning(
                f"[{recipient.username}] Обнаружен спам: {threshold} одинаковых сообщений подряд"
            )
            return True

        return False
