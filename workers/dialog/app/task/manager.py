import asyncio
from functools import partial

from telethon import TelegramClient
from telethon.events import NewMessage
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.task.ai_service import AIService
from app.task.telegram_service import TelegramService
from app.utils.logger import Logger


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

    def setup_event_handlers(self):
        """Регистрирует обработчики событий"""
        self.client.add_event_handler(
            partial(
                self._on_new_message,
                client=self.client,
                project=self.project,
                account=self.account,
                logger=self.logger,
                stop_event=self.stop_event,
            ),
            NewMessage(),
        )

    async def _on_new_message(
        self,
        event: NewMessage.Event,
        client: TelegramClient,
        project: orm.Project,
        account: orm.Account,
        logger: Logger,
        stop_event: asyncio.Event,
    ):
        """Обработчик входящих сообщений"""
        try:
            sender = await event.get_sender()
            if not sender.username:
                return

            text = event.raw_text

            # Находим recipient
            recipient = await orm.Recipient.get_or_none(username=sender.username)
            if not recipient:
                return

            # Получаем или создаём диалог
            dialog = await orm.Dialog.get_or_none(recipient=recipient)
            if not dialog:
                dialog = await orm.Dialog.create(
                    recipient=recipient, status=enums.DialogStatus.INIT
                )

            if dialog.status == enums.DialogStatus.CLOSE:
                logger.info(f"Диалог с {recipient.username} уже закрыт, пропускаем")
                return

            # Сохраняем сообщение от получателя
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.RECIPIENT,
                tg_message_id=event.id,
                text=text,
            )

            logger.info(f"[{recipient.username}] Получено новое сообщение")

            # Проверяем лимит сообщений
            messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

            if len(messages) >= project.dialog_limit:
                await self._close_dialog(dialog, recipient, "лимит сообщений")
                await self._check_and_stop_if_needed()
                return

            # Генерируем и отправляем ответ
            await self._generate_and_send_response(event, dialog, recipient, messages)

        except Exception as e:
            logger.error(f"Ошибка в on_new_message: {e}")
            import traceback

            logger.error(traceback.format_exc())

    async def _generate_and_send_response(
        self,
        event,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
    ):
        """Генерирует ответ от AI и отправляет его"""

        # Показываем "печатает..."
        async with self.client.action(event.chat_id, "typing"):  # type: ignore
            try:
                ai_response, new_status = await asyncio.wait_for(
                    self.ai_service.get_response_with_status(
                        self.project.prompt, messages, self.logger
                    ),
                    timeout=30,
                )
                # Имитация печатания
                await asyncio.sleep(5)  # можно сделать random.randint(3, 8)

            except asyncio.TimeoutError:
                self.logger.warning(f"[{recipient.username}] OpenAI timeout")
                return

        if not ai_response:
            self.logger.warning(f"[{recipient.username}] AI не вернул ответ")
            return

        # Обновляем статус диалога
        await self._update_dialog_status(dialog, recipient, new_status, messages)

        # Отправляем сообщение
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

            if new_status == enums.DialogStatus.CLOSE:
                dialog.finished_at = tz.now()

            await dialog.save()
            self.logger.info(
                f"[{recipient.username}] Статус: {old_status.value} -> {new_status.value}"
            )

            # Проверяем лимиты только при закрытии
            if new_status == enums.DialogStatus.CLOSE:
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
        dialog.status = enums.DialogStatus.CLOSE
        dialog.finished_at = tz.now()
        await dialog.save()
        self.logger.info(f"[{recipient.username}] Диалог закрыт: {reason}")

    async def _check_and_stop_if_needed(self):
        """Проверяет условия для остановки task"""

        # Проверяем дневной лимит для аккаунта
        counter = await orm.AccountActionCounter.filter(
            account=self.account,
            action=enums.AccountAction.NEW_DIALOG,
            date=tz.now().date(),
        ).first()

        dialogs_today = counter.count if counter else 0

        if dialogs_today >= self.project.out_daily_limit:
            self.logger.info(
                f"Достигнут дневной лимит: {dialogs_today}/{self.project.out_daily_limit}"
            )
            self.stop_event.set()
            return

        # Получаем все mailing_id для проекта
        mailing_ids = await orm.Mailing.filter(project=self.project).values_list(
            "id", flat=True
        )

        if not mailing_ids:
            return

        # Подсчитываем активные диалоги
        active_dialogs = await orm.Dialog.filter(
            recipient__mailing_id__in=mailing_ids,
            status__not_in=[enums.DialogStatus.CLOSE],
        ).count()

        closed_today = await orm.Dialog.filter(
            recipient__mailing_id__in=mailing_ids,
            status=enums.DialogStatus.CLOSE,
            finished_at__gte=tz.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
        ).count()

        self.logger.info(
            f"[Аккаунт {self.account.id}] Статус: активных={active_dialogs}, "
            f"закрыто сегодня={closed_today}, всего={dialogs_today}/{self.project.out_daily_limit}"
        )
