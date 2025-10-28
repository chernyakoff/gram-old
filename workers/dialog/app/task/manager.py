import asyncio
import random
from functools import partial

from telethon import TelegramClient
from telethon.events import NewMessage
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.utils.logger import Logger

from .ai_service import AIService
from .telegram_service import TelegramService


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

    def register_session_recipient(self, recipient_id: int):
        """Регистрирует recipient как часть текущей сессии"""
        self.session_recipients_ids.add(recipient_id)

    def setup_event_handlers(self):
        """Регистрирует обработчики событий"""
        self.client.add_event_handler(
            partial(
                self._on_new_message,
            ),
            NewMessage(),
        )

    async def _on_new_message(
        self,
        event: NewMessage.Event,
    ):
        """Обработчик входящих сообщений"""
        try:
            sender = await event.get_sender()
            if not sender.username:
                return

            text = event.raw_text

            # Находим recipient
            recipient = await orm.Recipient.filter(
                username=sender.username, id__in=self.session_recipients_ids
            ).first()

            if not recipient:
                return

            # Получаем или создаём диалог
            dialog = await orm.Dialog.get_or_none(recipient=recipient)
            if not dialog:
                dialog = await orm.Dialog.create(
                    recipient=recipient,
                    status=enums.DialogStatus.INIT,
                    account=self.account,
                )

            if dialog.status == enums.DialogStatus.COMPLETE:
                self.logger.info(
                    f"[{recipient.username}] Диалог уже закрыт, пропускаем"
                )
                return

            # Сохраняем сообщение от получателя
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.RECIPIENT,
                tg_message_id=event.id,
                text=text,
            )

            self.logger.info(f"[{recipient.username}] Получено новое сообщение")

            # Проверяем лимит сообщений
            messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

            if len(messages) >= self.project.dialog_limit:
                await self._close_dialog(dialog, recipient, "лимит сообщений")
                await self._check_and_stop_if_needed()
                return

            # Генерируем и отправляем ответ
            await self._generate_and_send_response(event, dialog, recipient, messages)

        except Exception as e:
            self.logger.error(f"Ошибка в on_new_message: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    async def _generate_and_send_response(
        self,
        event,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
    ):
        """Генерирует ответ от AI и отправляет его"""

        # Показываем "печатает..."
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
                        self.stop_event.set()
                        return
                    else:
                        await asyncio.sleep(2)  # пауза перед повтором
                        continue  # пробуем снова

                # Имитация печатания
                break  # получили ответ, выходим из цикла

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"[{recipient.username}] OpenAI timeout (attempt {attempt})"
                )
                if attempt == MAX_RETRIES:
                    self.stop_event.set()
                    return
                else:
                    await asyncio.sleep(2)  # пауза перед повтором

        if not ai_response:  # такого не может быть - добавил для type check
            return
        # Обновляем статус диалога
        await self._update_dialog_status(dialog, recipient, new_status, messages)

        await asyncio.sleep(random.randint(3, 10))
        await self.client.send_read_acknowledge(event.chat_id)  # type: ignore

        async with self.client.action(event.chat_id, "typing"):  # type: ignore
            # Отправляем сообщение
            await asyncio.sleep(random.randint(3, 10))
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
        """Обновляет статус диалога"""

        if new_status and new_status != dialog.status:
            old_status = dialog.status
            dialog.status = new_status

            if new_status == enums.DialogStatus.COMPLETE:
                dialog.finished_at = tz.now()

            await dialog.save()
            self.logger.info(
                f"[{recipient.username}] Статус: {old_status.value} -> {new_status.value}"
            )

            # Проверяем лимиты только при закрытии
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
        """Закрывает диалог"""
        dialog.status = enums.DialogStatus.COMPLETE
        dialog.finished_at = tz.now()
        await dialog.save()
        self.logger.info(f"[{recipient.username}] Диалог закрыт: {reason}")

    async def _check_and_stop_if_needed(self):
        """Проверяет условия для остановки task"""

        # 1. Проверяем дневной лимит для аккаунта
        counter = await orm.AccountActionCounter.filter(
            account=self.account,
            action=enums.AccountAction.NEW_DIALOG,
            date=tz.now().date(),
        ).first()

        dialogs_today = counter.count if counter else 0

        if dialogs_today >= self.project.out_daily_limit:
            self.logger.info(
                f"🛑 Достигнут дневной лимит: {dialogs_today}/{self.project.out_daily_limit}"
            )
            self.stop_event.set()
            return

        # 2. Проверяем статус диалогов ТЕКУЩЕЙ СЕССИИ
        if not self.session_recipients_ids:
            return

        # Считаем активные и закрытые диалоги только для recipients текущей сессии
        active_session_dialogs = await orm.Dialog.filter(
            recipient_id__in=self.session_recipients_ids,
            status__not_in=[enums.DialogStatus.COMPLETE],
        ).count()

        closed_session_dialogs = await orm.Dialog.filter(
            recipient_id__in=self.session_recipients_ids,
            status=enums.DialogStatus.COMPLETE,
        ).count()

        total_session_dialogs = len(self.session_recipients_ids)

        self.logger.info(
            f"[Аккаунт {self.account.id}] Сессия: "
            f"активных={active_session_dialogs}/{total_session_dialogs}, "
            f"закрытых={closed_session_dialogs}/{total_session_dialogs}"
        )

        # КЛЮЧЕВАЯ ПРОВЕРКА: Если все диалоги сессии завершены
        if active_session_dialogs == 0 and closed_session_dialogs > 0:
            self.logger.info(
                f"🛑 Все диалоги текущей сессии завершены "
                f"({closed_session_dialogs}/{total_session_dialogs})"
            )
            self.stop_event.set()
            return
