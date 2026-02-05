import asyncio
import random
from datetime import datetime, timedelta
from functools import partial

import pytz
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.events import NewMessage
from telethon.tl.functions.messages import GetPeerDialogsRequest
from telethon.tl.types import InputDialogPeer
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.common.utils.notify import BotNotify, notify_complete_dialog
from app.common.utils.prompt import get_name_addon
from app.tasks.dialog.session_timer import SessionTimer
from app.utils.logger import Logger

from .ai_service import AIService
from .telegram_service import TelegramService

# Константы
WAIT_FOR_REPLY_MINUTES = 5
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

        self.message_buffers: dict[int, list] = {}  # Оставляем только буфер

        # Создаём таймер сессии
        self.session_timer = SessionTimer(
            initial_minutes=5,
            on_timeout=lambda: self.stop_event.set(),
            logger=self.logger,
        )

        self.ai_service = AIService(self.account.user)
        self.telegram_service = TelegramService(client, logger)

    async def check_and_process_dialogs(self) -> tuple[int, int]:
        """
        Проверяет диалоги в правильном порядке:
        1. Отправляет system-сообщения
        2. Получает новые сообщения от юзеров
        3. Генерирует AI-ответы с учётом ВСЕГО контекста

        Возвращает: (dialogs_with_system, dialogs_with_replies)
        """
        try:
            recovered = await self._recover_stuck_dialogs(min_age_minutes=10)
            if recovered > 0:
                self.logger.info(f"🔄 Восстановлено {recovered} зависших диалогов")
        except Exception as e:
            self.logger.error(f"Ошибка при восстановлении диалогов: {e}")

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
                    self.session_timer.reset(5)  # ДОБАВИТЬ ЭТУ СТРОКУ
                    await asyncio.sleep(random.randint(5, 10))

                # ШАГ 2: Проверяем новые сообщения от юзера в Telegram
                new_messages = await self._get_new_messages_from_telegram(dialog)

                if not new_messages:
                    continue

                # ШАГ 3: Сохраняем новые сообщения в БД
                for msg in new_messages:
                    await orm.Message.create(
                        dialog=dialog,
                        sender=enums.MessageSender.RECIPIENT,
                        tg_message_id=msg.id,
                        text=msg.text or "",
                        created_at=msg.date,
                    )

                dialogs_with_replies += 1
                self.session_timer.reset(5)

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
        messages = await orm.Message.filter(dialog=dialog, ui_only=False).order_by(
            "created_at"
        )

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
                    self.session_timer.reset(5)
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
            await orm.Message.filter(dialog=dialog, ui_only=False)
            .order_by("-created_at")
            .first()
        )

        if not last_db_message or not last_db_message.tg_message_id:
            return []

        # Получаем новые сообщения из Telegram
        new_messages = []
        try:
            async for msg in self.client.iter_messages(
                peer, min_id=last_db_message.tg_message_id
            ):
                if msg.id == last_db_message.tg_message_id:
                    continue
                if msg.out:  # Пропускаем исходящие
                    continue
                new_messages.append(msg)
        except Exception as e:
            # Если peer_id невалиден - переза прашиваем entity
            if "PeerIdInvalidError" in str(type(e)):
                self.logger.warning(
                    f"[{dialog.recipient.username}] PeerIdInvalid, обновляем entity"
                )
                # Обновляем entity
                await self.telegram_service.get_entity(dialog.recipient)
                peer = self.telegram_service._get_peer(dialog.recipient)
                if not peer:
                    return []

                # Повторная попытка
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

        """ 
        async for msg in self.client.iter_messages(
            peer, min_id=last_db_message.tg_message_id
        ):
            if msg.id == last_db_message.tg_message_id:
                continue
            if msg.out:  # Пропускаем исходящие
                continue
            new_messages.append(msg) """

        if new_messages:
            new_messages.sort(key=lambda m: m.date)

        return new_messages

    def setup_event_handlers(self):
        """Регистрирует обработчики событий"""
        self.client.add_event_handler(
            partial(self._on_new_message),
            NewMessage(),
        )

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
                        await orm.Message.filter(dialog=dialog, ui_only=False)
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
                        self.session_timer.reset(5)

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

            self.session_timer.reset(5)

            # Добавляем сообщение в буфер
            if dialog.id not in self.message_buffers:
                self.message_buffers[dialog.id] = []
            self.message_buffers[dialog.id].append(event)

            # Создаём задачу ожидания дополнительных сообщений
            asyncio.create_task(self._wait_and_process_messages(dialog, recipient))

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

    async def _process_dialog_reply(
        self, dialog: orm.Dialog, recipient: orm.Recipient, events: list
    ):
        """Обрабатывает диалог и отправляет ответ"""
        if not events:
            self.logger.warning(
                f"[{recipient.username}] _process_dialog_reply вызван с пустыми events"
            )
            return

        # НОВОЕ: Помечаем что этот диалог в обработке
        self.session_timer.add(3)

        try:
            # Проверяем лимит сообщений
            messages = await orm.Message.filter(dialog=dialog, ui_only=False).order_by(
                "created_at"
            )

            if len(messages) >= self.project.dialog_limit:
                return

            if await self._check_spam_messages(messages, recipient):
                self.logger.warning(
                    f"[{recipient.username}] Обнаружен спам - пропускаем"
                )
                return

            # НОВОЕ: Если диалог в статусе MANUAL - не генерируем AI ответ
            if dialog.status == enums.DialogStatus.MANUAL:
                self.logger.info(
                    f"[{recipient.username}] Диалог в режиме MANUAL, "
                    f"ожидаем SYSTEM сообщения от оператора"
                )
                # Запускаем ожидание следующего ответа

                return

            # ИЗМЕНЕНО: Получаем булевый результат - продолжать ли диалог
            await self._generate_and_send_response(
                events[0], dialog, recipient, messages
            )

        except Exception as e:
            self.logger.error(f"Ошибка в _process_dialog_reply: {e}")

    async def _generate_and_send_response(
        self,
        event,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
    ):
        """
        Генерирует ответ от AI и отправляет его.

        Returns:
            bool: True если нужно продолжить ожидание ответа,
                False если диалог завершён
        """

        fresh_messages = await orm.Message.filter(
            dialog=dialog, ui_only=False
        ).order_by("created_at")

        # Ищем неотправленные system-сообщения в конце
        unsent_system = []
        for msg in reversed(fresh_messages):
            if msg.sender == enums.MessageSender.SYSTEM and msg.tg_message_id is None:
                unsent_system.insert(0, msg)
            elif (
                msg.sender == enums.MessageSender.SYSTEM
                and msg.tg_message_id is not None
            ):
                continue  # Пропускаем отправленные SYSTEM
            else:
                break  # Прерываемся на первом не-SYSTEM

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
                    self.session_timer.reset(5)
                    await asyncio.sleep(random.randint(2, 5))

            # НОВОЕ: Если режим MANUAL - не генерируем AI ответ, возвращаемся
            self.logger.info(
                f"[{recipient.username}] Режим MANUAL активен, пропускаем AI генерацию"
            )
            # ВАЖНО: Возвращаем True, т.к. диалог продолжается в MANUAL режиме
            return

        # НОВОЕ: Дополнительная проверка статуса перед генерацией
        if dialog.status == enums.DialogStatus.MANUAL:
            self.logger.info(
                f"[{recipient.username}] Диалог в MANUAL режиме, AI ответ не генерируется"
            )
            # ВАЖНО: Возвращаем True, т.к. диалог продолжается в MANUAL режиме
            return

        # Далее идет существующий код генерации AI ответа
        MAX_RETRIES = 3

        name_addon = get_name_addon(self.account, recipient)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ai_response, new_status = await asyncio.wait_for(
                    self.ai_service.get_response_with_status(
                        self.prompt,
                        dialog,
                        messages,
                        name_addon,
                        self.project,
                        self.telegram_service,
                        recipient,
                        self.logger,
                    ),
                    timeout=60,
                )
                if ai_response == "__TERMINAL_STATUS__":
                    self.logger.info(
                        f"[{recipient.username}] AI вернул терминальный статус: {new_status.value}"  # type: ignore
                    )

                    # Обновляем статус диалога
                    await self._update_dialog_status(
                        dialog, recipient, new_status, messages
                    )

                    # Для терминальных статусов не нужно отправлять сообщение
                    if new_status == enums.DialogStatus.NEGATIVE:
                        self.logger.info(
                            f"[{recipient.username}] Диалог завершён со статусом NEGATIVE"
                        )
                    elif new_status == enums.DialogStatus.OPERATOR:
                        self.logger.info(f"[{recipient.username}] Требуется оператор")
                        asyncio.create_task(
                            BotNotify.warning(
                                self.account.user_id,
                                f"@{recipient.username} требует оператора",
                            )
                        )

                    return

                if not ai_response:
                    self.logger.warning(
                        f"[{recipient.username}] AI не вернул ответ (attempt {attempt})"
                    )
                    if attempt == MAX_RETRIES:
                        # Останавливаем диалог при критической ошибке AI
                        self.logger.error(
                            f"[{recipient.username}] Критическая ошибка AI"
                        )
                        # ВАЖНО: Уменьшаем счётчик

                        # ВАЖНО: Возвращаем False = диалог завершён
                        return
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
                    self.logger.error(f"[{recipient.username}] AI timeout")
                    # ВАЖНО: Возвращаем False = диалог завершён
                    return
                else:
                    await asyncio.sleep(2)

        if not ai_response:
            # ВАЖНО: Возвращаем False = диалог завершён
            return

        if (
            new_status == enums.DialogStatus.CLOSING
            and dialog.status != enums.DialogStatus.CLOSING
        ):
            asyncio.create_task(notify_complete_dialog(dialog, self.account))  # type: ignore

        # Обновляем статус диалога
        await self._update_dialog_status(dialog, recipient, new_status, messages)

        # Если AI вернул COMPLETE - диалог завершён
        if dialog.status == enums.DialogStatus.COMPLETE or ai_response == "COMPLETE":
            self.logger.info(f"[{recipient.username}] AI завершил диалог (COMPLETE)")
            asyncio.create_task(notify_complete_dialog(dialog, self.account))  # type: ignore
            # ВАЖНО: Уменьшаем счётчик активных диалогов
            return

        # НОВОЕ: Проверяем терминальный статус NEGATIVE
        if dialog.status == enums.DialogStatus.NEGATIVE:
            self.logger.info(
                f"[{recipient.username}] AI установил статус NEGATIVE - диалог завершён"
            )

            return

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
            return

        if event:
            # Обычный режим - с эффектами
            await asyncio.sleep(random.randint(3, 10))
            await self.client.send_read_acknowledge(event.chat_id)

            # Показываем "печатает..."
            async with self.client.action(event.chat_id, "typing"):  # type: ignore
                await asyncio.sleep(random.randint(10, 20))
                msg = await self.telegram_service.send_message(recipient, ai_response)
        else:
            # Режим восстановления - без эффектов
            msg = await self.telegram_service.send_message(recipient, ai_response)

        if msg:
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=ai_response,
            )
            self.logger.info(f"[{recipient.username}] Отправлен ответ")
            self.session_timer.reset(5)

        return

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

            # Только AI может установить статус COMPLEPTE
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

    async def _find_stuck_dialogs(self, min_age_minutes: int = 10) -> list[orm.Dialog]:
        """
        Находит зависшие диалоги по критериям:
        - Статус в (INIT, ENGAGE, OFFER, CLOSING)
        - finished_at IS NULL
        - Последнее сообщение от RECIPIENT
        - Это сообщение старше min_age_minutes
        """
        active_statuses = [
            enums.DialogStatus.INIT,
            enums.DialogStatus.ENGAGE,
            enums.DialogStatus.OFFER,
            enums.DialogStatus.CLOSING,
        ]

        dialogs = await orm.Dialog.filter(
            account_id=self.account.id,
            status__in=active_statuses,
            finished_at__isnull=True,
        ).prefetch_related("recipient")

        stuck_dialogs = []
        cutoff_time = tz.now() - timedelta(minutes=min_age_minutes)

        for dialog in dialogs:
            last_message = (
                await orm.Message.filter(dialog=dialog, ui_only=False)
                .order_by("-created_at")
                .first()
            )

            if not last_message:
                continue

            if (
                last_message.sender == enums.MessageSender.RECIPIENT
                and last_message.created_at < cutoff_time
            ):
                stuck_dialogs.append(dialog)

        return stuck_dialogs

    async def _recover_stuck_dialogs(self, min_age_minutes: int = 10) -> int:
        """
        Восстанавливает зависшие диалоги

        Returns:
            Количество восстановленных диалогов
        """
        stuck_dialogs = await self._find_stuck_dialogs(min_age_minutes)

        if not stuck_dialogs:
            return 0

        self.logger.warning(
            f"🔄 Обнаружено {len(stuck_dialogs)} зависших диалогов "
            f"(без ответа > {min_age_minutes} мин)"
        )

        recovered = 0

        for dialog in stuck_dialogs:
            try:
                recipient = dialog.recipient

                self.logger.info(
                    f"🔧 Восстановление диалога {dialog.id} с @{recipient.username} "
                    f"(статус: {dialog.status.value})"
                )

                messages = await orm.Message.filter(
                    dialog=dialog, ui_only=False
                ).order_by("created_at")

                if not messages:
                    continue

                await self._generate_and_send_response(
                    event=None, dialog=dialog, recipient=recipient, messages=messages
                )

                recovered += 1
                await asyncio.sleep(random.randint(3, 7))

            except Exception as e:
                self.logger.error(f"Ошибка при восстановлении диалога {dialog.id}: {e}")
                import traceback

                self.logger.error(traceback.format_exc())
                continue

        if recovered > 0:
            self.logger.info(
                f"✅ Успешно восстановлено {recovered} из {len(stuck_dialogs)} диалогов"
            )

        return recovered

    # remnders ---------------------------------

    def _get_user_now(self) -> datetime:
        """Возвращает текущее время в timezone пользователя"""
        import pytz

        user_tz = pytz.timezone(self.account.user.timezone or "Europe/Moscow")
        return datetime.now(user_tz)

    def _is_morning_time(self, user_now: datetime) -> bool:
        """
        Проверяет что сейчас подходящее время для утреннего напоминания.
        Должно быть близко к project.send_time_start (±30 минут).
        """
        current_hour = user_now.hour
        current_minute = user_now.minute

        target_hour = self.project.send_time_start

        # Переводим в минуты от начала дня для удобства сравнения
        current_minutes = current_hour * 60 + current_minute
        target_minutes = target_hour * 60

        # Проверяем что разница не более 30 минут
        diff = abs(current_minutes - target_minutes)

        return diff <= 30  # magic number - частота запуска task

    async def _send_reminder_immediately(
        self, dialog: orm.Dialog, reminder_text: str
    ) -> bool:
        """
        Отправляет напоминание немедленно как сообщение от ACCOUNT (AI).
        Возвращает True если успешно отправлено.
        """
        try:
            recipient = dialog.recipient

            # Отправляем сразу через telegram
            msg = await self.telegram_service.send_message(recipient, reminder_text)

            if not msg:
                self.logger.error(
                    f"[{recipient.username}] Не удалось отправить напоминание"
                )
                return False
            else:
                self.session_timer.reset(5)

            # Сохраняем как обычное сообщение от ACCOUNT (AI)
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=reminder_text,
            )

            self.logger.info(
                f"[{recipient.username}] ✅ Напоминание отправлено: {reminder_text[:50]}..."
            )

            return True

        except Exception as e:
            self.logger.error(
                f"[{recipient.username}] Ошибка отправки напоминания: {e}"
            )
            return False

    async def _check_morning_reminders(self):
        """Проверяет и отправляет утренние напоминания"""

        if not self.project.use_calendar or not self.project.morning_reminder:
            return 0

        # Получаем сегодняшнюю дату в timezone пользователя
        user_now = self._get_user_now()
        today = user_now.date()

        # Проверяем что сейчас подходящее время (близко к send_time_start)
        if not self._is_morning_time(user_now):
            return 0

        # Находим встречи на сегодня для этого аккаунта
        meetings = await orm.Meeting.filter(
            dialog__account_id=self.account.id,
            start_at__date=today,
            status=orm.MeetingStatus.SCHEDULED,
        ).prefetch_related("dialog__recipient")

        sent_count = 0

        for meeting in meetings:
            # Проверяем что еще не отправляли
            already_sent = await orm.MorningReminderSent.exists(meeting=meeting)
            if already_sent:
                continue

            # Проверяем что это диалог из текущего проекта
            dialog = meeting.dialog
            if dialog.project_id != self.project.id:
                continue

            # Отправляем немедленно
            success = await self._send_reminder_immediately(
                dialog, self.project.morning_reminder
            )

            if success:
                dialog.status = enums.DialogStatus.CLOSING
                await dialog.save(update_fields=["status"])
                # Помечаем как отправленное
                await orm.MorningReminderSent.create(meeting=meeting)
                sent_count += 1

                # Задержка между напоминаниями
                await asyncio.sleep(random.randint(3, 7))

        return sent_count

    async def _check_meeting_reminders(self):
        """Проверяет и отправляет напоминания за час до встречи"""

        if not self.project.use_calendar or not self.project.meeting_reminder:
            return 0

        # Текущее время
        now = tz.now()

        # Ищем встречи которые начнутся через 45-75 минут
        hour_from_now_min = now + timedelta(minutes=45)
        hour_from_now_max = now + timedelta(minutes=75)

        meetings = await orm.Meeting.filter(
            dialog__account_id=self.account.id,
            start_at__gte=hour_from_now_min,
            start_at__lte=hour_from_now_max,
            status=orm.MeetingStatus.SCHEDULED,
        ).prefetch_related("dialog__recipient")

        sent_count = 0

        for meeting in meetings:
            # Проверяем что еще не отправляли
            already_sent = await orm.MeetingReminderSent.exists(meeting=meeting)
            if already_sent:
                continue

            # Проверяем что это диалог из текущего проекта
            dialog = meeting.dialog
            if dialog.project_id != self.project.id:
                continue

            # Форматируем текст напоминания с временем встречи
            reminder_text = self._format_meeting_reminder(
                self.project.meeting_reminder, meeting
            )

            # Отправляем немедленно
            success = await self._send_reminder_immediately(dialog, reminder_text)

            if success:
                dialog.status = enums.DialogStatus.CLOSING
                await dialog.save(update_fields=["status"])
                # Помечаем как отправленное
                await orm.MeetingReminderSent.create(meeting=meeting)
                sent_count += 1

                # Задержка между напоминаниями
                await asyncio.sleep(random.randint(3, 7))

        return sent_count

    def _format_meeting_reminder(self, template: str, meeting: orm.Meeting) -> str:
        """
        Форматирует текст напоминания, подставляя время встречи.
        Можно использовать плейсхолдеры: {time}, {date}
        """
        user_tz = pytz.timezone(self.account.user.timezone or "Europe/Moscow")
        meeting_time = meeting.start_at.astimezone(user_tz)

        return template.format(
            time=meeting_time.strftime("%H:%M"),
            TIME=meeting_time.strftime("%H:%M"),
            date=meeting_time.strftime("%d.%m.%Y"),
            DATE=meeting_time.strftime("%d.%m.%Y"),
            datetime=meeting_time.strftime("%d.%m.%Y %H:%M"),
            DATETIME=meeting_time.strftime("%d.%m.%Y %H:%M"),
        )

    async def check_and_send_reminders(self):
        """
        Проверяет и отправляет все типы напоминаний.
        Вызывается периодически в dialog_task.
        """
        try:
            morning_sent = await self._check_morning_reminders()
            meeting_sent = await self._check_meeting_reminders()

            total = morning_sent + meeting_sent

            if total > 0:
                self.logger.info(
                    f"📧 Отправлено напоминаний: "
                    f"утренних={morning_sent}, о встречах={meeting_sent}"
                )

            return total

        except Exception as e:
            self.logger.error(f"Ошибка при проверке напоминаний: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return 0
