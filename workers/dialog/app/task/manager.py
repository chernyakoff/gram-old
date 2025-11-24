import asyncio
import random
from datetime import timedelta
from functools import partial

from telethon import TelegramClient
from telethon.events import NewMessage
from tortoise import timezone as tz
from tortoise.expressions import Q

from app.common.models import enums, orm
from app.utils.logger import Logger
from app.utils.notify import notify_complete_dialog

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
        account: orm.Account,
        logger: Logger,
        stop_event: asyncio.Event,
    ):
        self.client = client
        self.project = project
        self.account = account
        self.logger = logger
        self.stop_event = stop_event

        self.ai_service = AIService()
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

    def register_session_recipient(self, recipient_id: int):
        """Регистрирует recipient как часть текущей сессии"""
        self.session_recipients_ids.add(recipient_id)

    async def start_waiting_for_first_reply(
        self, dialog: orm.Dialog, recipient: orm.Recipient
    ):
        """Запускает ожидание ответа на первое сообщение"""
        self.active_dialogs_count += 1
        await self._wait_for_reply(dialog, recipient)

    def setup_event_handlers(self):
        """Регистрирует обработчики событий"""
        self.client.add_event_handler(
            partial(self._on_new_message),
            NewMessage(),
        )

    async def check_old_dialogs_for_new_messages(self) -> int:
        """
        Проверяет старые незавершенные диалоги на новые сообщения.
        Возвращает количество диалогов, в которых найдены новые сообщения.
        """
        dialogs_with_messages = 0

        try:
            # Получаем все незавершенные диалоги для этого аккаунта
            dialogs = (
                await orm.Dialog.filter(
                    account_id=self.account.id,
                )
                .exclude(finished_at__isnull=True)
                .prefetch_related("recipient", "messages")
            )

            self.logger.info(
                f"Проверка {len(dialogs)} старых диалогов на новые сообщения"
            )

            for dialog in dialogs:
                try:
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
                        dialog.recipient.username, min_id=last_db_message.tg_message_id
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
        try:
            # Проверяем лимит сообщений
            messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

            if len(messages) >= self.project.dialog_limit:
                await self._close_dialog(dialog, recipient, "лимит сообщений")
                # Уменьшаем счётчик так как диалог больше не ждёт ответа
                self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
                await self._check_and_stop_if_needed()
                return

            # Генерируем ответ от AI
            await self._generate_and_send_response(
                events[0], dialog, recipient, messages
            )

            # Увеличиваем счетчик активных диалогов
            self.active_dialogs_count += 1

            # Запускаем ожидание ответа (5 минут)
            await self._wait_for_reply(dialog, recipient)

        except Exception as e:
            self.logger.error(f"Ошибка в _process_dialog_reply: {e}")

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
                    # Уменьшаем счетчик (диалог продолжается, но это ожидание завершено)
                    self.active_dialogs_count -= 1
                    return

                # Проверяем, не остановлена ли задача
                if self.stop_event.is_set():
                    self.active_dialogs_count -= 1
                    return

                await asyncio.sleep(5)  # Проверяем каждые 5 секунд

            # Если не дождались ответа - закрываем диалог
            self.logger.info(
                f"[{recipient.username}] Не получен ответ за {WAIT_FOR_REPLY_MINUTES} минут, останавливаем диалог"
            )
            await self._close_dialog(dialog, recipient, "нет ответа")

            # Уменьшаем счетчик активных диалогов
            self.active_dialogs_count -= 1

            # Проверяем, может пора завершаться
            await self._check_and_stop_if_needed()

        except Exception as e:
            self.logger.error(f"Ошибка в _wait_for_reply: {e}")
            self.active_dialogs_count = max(0, self.active_dialogs_count - 1)

    async def _generate_and_send_response(
        self,
        event,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
    ):
        """Генерирует ответ от AI и отправляет его"""

        MAX_RETRIES = 3

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ai_response, new_status = await asyncio.wait_for(
                    self.ai_service.get_response_with_status(
                        self.project.prompt, dialog.status, messages, self.logger
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
                        # Уменьшаем счётчик
                        self.active_dialogs_count = max(
                            0, self.active_dialogs_count - 1
                        )
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
                    await self._close_dialog(dialog, recipient, "AI timeout")
                    # Уменьшаем счётчик
                    self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
                    return
                else:
                    await asyncio.sleep(2)

        if not ai_response:
            return

        # Обновляем статус диалога
        await self._update_dialog_status(dialog, recipient, new_status, messages)

        # Если AI вернул COMPLETE - диалог завершён
        if ai_response == "COMPLETE":
            self.logger.info(f"[{recipient.username}] AI завершил диалог (COMPLETE)")
            asyncio.create_task(notify_complete_dialog(dialog, self.account))
            # Уменьшаем счётчик активных диалогов
            self.active_dialogs_count = max(0, self.active_dialogs_count - 1)
            await self._check_and_stop_if_needed()
            return

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
            if new_status == enums.DialogStatus.COMPLETE:
                dialog.finished_at = tz.now()

            await dialog.save()
            self.logger.info(
                f"[{recipient.username}] AI изменил статус: {old_status.value} -> {new_status.value}"
            )

            # Если AI установил COMPLETE - проверяем условия завершения
            if new_status == enums.DialogStatus.COMPLETE:
                await self._check_and_stop_if_needed()

        elif not new_status:
            # Эвристика: если 2+ сообщения от пользователя
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

        # 1. Проверяем дневной лимит для аккаунта
        counter = await orm.AccountActionCounter.filter(
            account=self.account,
            action=enums.AccountAction.NEW_DIALOG,
            date=tz.now().date(),
        ).first()

        dialogs_today = counter.count if counter else 0

        if dialogs_today >= self.account.out_daily_limit:
            self.logger.info(
                f"🛑 Достигнут дневной лимит: {dialogs_today}/{self.account.out_daily_limit}"
            )
            self.stop_event.set()
            return

        # 2. Если нет диалогов в сессии - завершаемся
        if not self.session_recipients_ids:
            self.logger.info("🛑 Нет диалогов в текущей сессии")
            self.stop_event.set()
            return

        # 3. Считаем незавершенные диалоги сессии
        # Теперь полагаемся только на счётчик в памяти, так как статус COMPLETE ставит только AI
        total_session_dialogs = len(self.session_recipients_ids)

        self.logger.info(
            f"[Аккаунт {self.account.id}] Проверка завершения: "
            f"всего_в_сессии={total_session_dialogs}, "
            f"ожидающих_ответа_в_памяти={self.active_dialogs_count}"
        )

        # 4. КЛЮЧЕВАЯ ПРОВЕРКА: если нет диалогов ожидающих ответа
        if self.active_dialogs_count == 0 and total_session_dialogs > 0:
            self.logger.info(f"🛑 Нет диалогов ожидающих ответа (сессия завершена)")
            self.stop_event.set()
            return
