import asyncio
import random
from datetime import datetime, timedelta

from telethon.errors import FloodWaitError
from tortoise import timezone as tz

from app.common.models import enums, orm
from app.common.utils.functions import generate_message, normalize_dashes, randomize_message
from app.common.utils.notify import BotNotify, notify_complete_dialog
from app.utils.logger import Logger

from .dialog_ai import DialogAI
from .dialog_delivery import DeliveryService
from .dialog_log import (
    log_ai_critical,
    log_ai_no_response,
    log_ai_terminal,
    log_ai_timeout,
    log_ai_timeout_final,
)
from .dialog_scanner import DialogScanner
from .reminder_service import ReminderService
from .session_timer import SessionTimer


class DialogProcessor:
    """Зона ответственности: бизнес-логика диалогов и AI."""

    def __init__(
        self,
        account: orm.Account,
        project: orm.Project,
        logger: Logger,
        dialog_ai: DialogAI,
        delivery: DeliveryService,
        session_timer: SessionTimer,
        stop_event: asyncio.Event,
        scanner: DialogScanner,
        reminders: ReminderService,
    ):
        self.account = account
        self.project = project
        self.logger = logger
        self.dialog_ai = dialog_ai
        self.delivery = delivery
        self.session_timer = session_timer
        self.stop_event = stop_event
        self.scanner = scanner
        self.reminders = reminders

    async def start_new_dialogs(
        self, recipients_id: list[int], end_time: datetime | None = None
    ) -> int:
        new_dialogs_started = 0

        for recipient_id in recipients_id:
            recipient = await orm.Recipient.get_or_none(id=recipient_id)
            if not recipient:
                continue

            entity = await self.scanner.ensure_entity(recipient)
            if not entity:
                continue

            dialog_exists = await orm.Dialog.get_or_none(recipient=recipient)
            if dialog_exists:
                continue

            first_message = generate_message(self.project.first_message)
            first_message = randomize_message(first_message)
            first_message = normalize_dashes(first_message)

            msg = await self.delivery.send_plain(recipient, first_message)
            if not msg:
                continue

            dialog = await orm.Dialog.create(
                recipient=recipient,
                status=enums.DialogStatus.INIT,
                account_id=self.account.id,
            )

            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=first_message,
            )

            new_dialogs_started += 1
            self.session_timer.reset(5)

            if self.stop_event.is_set() or (
                end_time is not None and tz.now() > end_time
            ):
                break

            await asyncio.sleep(random.randint(5, 30))

        return new_dialogs_started

    async def check_and_process_dialogs(self) -> tuple[int, int]:
        try:
            recovered = await self._recover_stuck_dialogs(min_age_minutes=10)
            if recovered > 0:
                self.logger.info(f"🔄 Восстановлено {recovered} зависших диалогов")
        except Exception as e:
            self.logger.error(f"Ошибка при восстановлении диалогов: {e}")

        dialogs = await self.scanner.get_active_dialogs(self.account.id)

        dialogs_with_system = 0
        dialogs_with_replies = 0

        for dialog in dialogs:
            try:
                has_system = await self._process_system_messages_for_dialog(dialog)
                if has_system:
                    dialogs_with_system += 1
                    self.session_timer.reset(5)
                    await asyncio.sleep(random.randint(5, 10))

                new_messages = await self.scanner.get_new_messages_from_telegram(dialog)

                if not new_messages:
                    continue

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

                await self.process_dialog_reply(dialog, dialog.recipient, new_messages)

            except FloodWaitError:
                self.logger.warning("FloodWait при обработке диалогов - прерываем")
                return dialogs_with_system, dialogs_with_replies
            except Exception as e:
                self.logger.error(f"Ошибка при обработке диалога {dialog.id}: {e}")
                import traceback

                self.logger.error(traceback.format_exc())
                continue

        return dialogs_with_system, dialogs_with_replies

    async def check_old_dialogs_for_new_messages(self) -> int:
        dialogs_with_messages = 0

        try:
            self.logger.info("Проверка старых диалогов на новые сообщения")

            results = await self.scanner.check_old_dialogs_for_new_messages(
                self.account.id
            )

            for dialog, new_messages in results:
                try:
                    self.logger.info(
                        f"[{dialog.recipient.username}] Найдено {len(new_messages)} новых сообщений"
                    )

                    for msg in new_messages:
                        await orm.Message.create(
                            dialog=dialog,
                            sender=enums.MessageSender.RECIPIENT,
                            tg_message_id=msg.id,
                            text=msg.text or "",
                        )

                    await self.process_dialog_reply(
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

    async def check_and_send_reminders(self):
        return await self.reminders.check_and_send_reminders()

    async def process_dialog_reply(
        self,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        events: list,
        messages: list[orm.Message] | None = None,
    ):
        if not events:
            self.logger.warning(
                f"[{recipient.username}] process_dialog_reply вызван с пустыми events"
            )
            return

        self.session_timer.add(3)

        try:
            if await self._process_system_messages_for_dialog(dialog):
                return

            if messages is None:
                messages = await orm.Message.filter(
                    dialog=dialog, ui_only=False
                ).order_by("created_at")

            if len(messages) >= self.project.dialog_limit:
                return

            if await self._check_spam_messages(messages, recipient):
                self.logger.warning(
                    f"[{recipient.username}] Обнаружен спам - пропускаем"
                )
                return

            if dialog.status == enums.DialogStatus.MANUAL:
                self.logger.info(
                    f"[{recipient.username}] Диалог в режиме MANUAL, "
                    "ожидаем SYSTEM сообщения от оператора"
                )
                return

            await self._generate_and_send_response(
                events[0], dialog, recipient, messages
            )

        except Exception as e:
            self.logger.error(f"Ошибка в process_dialog_reply: {e}")

    async def _process_system_messages_for_dialog(self, dialog: orm.Dialog) -> bool:
        messages = await orm.Message.filter(dialog=dialog, ui_only=False).order_by(
            "created_at"
        )

        if not messages:
            return False

        system_messages = []
        for msg in reversed(messages):
            if msg.sender == enums.MessageSender.SYSTEM and msg.tg_message_id is None:
                system_messages.insert(0, msg)
            elif (
                msg.sender == enums.MessageSender.SYSTEM
                and msg.tg_message_id is not None
            ):
                continue
            else:
                break

        if not system_messages:
            return False

        if dialog.status != enums.DialogStatus.MANUAL:
            self.logger.info(
                f"[{dialog.recipient.username}] Обнаружены SYSTEM сообщения, "
                f"переключение в режим MANUAL (было: {dialog.status.value})"
            )
            dialog.status = enums.DialogStatus.MANUAL
            await dialog.save(update_fields=["status"])

        for sys_msg in system_messages:
            try:
                msg = await self.delivery.send_plain(dialog.recipient, sys_msg.text)

                if msg:
                    sys_msg.tg_message_id = msg.id
                    await sys_msg.save(update_fields=["tg_message_id"])
                    self.session_timer.reset(5)
                    self.logger.info(
                        f"[{dialog.recipient.username}] Отправлено MANUAL system: {sys_msg.text[:50]}"
                    )

                    await asyncio.sleep(random.randint(2, 5))
            except Exception as e:
                self.logger.error(
                    f"Ошибка отправки system-сообщения {sys_msg.id}: {e}"
                )
                continue

        return True

    async def _get_ai_reply_with_retry(
        self,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
        max_retries: int = 3,
    ) -> tuple[str | None, enums.DialogStatus | None, bool] | None:
        for attempt in range(1, max_retries + 1):
            try:
                ai_response, new_status, is_terminal = await self.dialog_ai.get_reply(
                    dialog,
                    messages,
                    recipient,
                    timeout_sec=60,
                )

                if is_terminal:
                    return ai_response, new_status, True

                if not ai_response:
                    log_ai_no_response(self.logger, recipient, attempt)
                    if attempt == max_retries:
                        log_ai_critical(self.logger, recipient)
                        return None
                    await asyncio.sleep(2)
                    continue

                return ai_response, new_status, False

            except asyncio.TimeoutError:
                log_ai_timeout(self.logger, recipient, attempt)
                if attempt == max_retries:
                    log_ai_timeout_final(self.logger, recipient)
                    return None
                await asyncio.sleep(2)

        return None

    async def _handle_terminal_status(
        self,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        new_status: enums.DialogStatus | None,
        messages: list[orm.Message],
    ):
        if not new_status:
            return

        log_ai_terminal(self.logger, recipient, new_status)

        await self._apply_status(dialog, recipient, new_status, messages)

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

    async def _generate_and_send_response(
        self,
        event,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        messages: list[orm.Message],
    ):
        result = await self._get_ai_reply_with_retry(dialog, recipient, messages)
        if not result:
            return

        ai_response, new_status, is_terminal = result

        if is_terminal:
            await self._handle_terminal_status(
                dialog, recipient, new_status, messages
            )
            return

        if not ai_response:
            return

        if (
            new_status == enums.DialogStatus.CLOSING
            and dialog.status != enums.DialogStatus.CLOSING
        ):
            asyncio.create_task(notify_complete_dialog(dialog, self.account))  # type: ignore

        await self._apply_status(dialog, recipient, new_status, messages)

        if dialog.status == enums.DialogStatus.COMPLETE or ai_response == "COMPLETE":
            self.logger.info(f"[{recipient.username}] AI завершил диалог (COMPLETE)")
            asyncio.create_task(notify_complete_dialog(dialog, self.account))  # type: ignore
            return

        if dialog.status == enums.DialogStatus.NEGATIVE:
            self.logger.info(
                f"[{recipient.username}] AI установил статус NEGATIVE - диалог завершён"
            )
            return

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

        msg = await self.delivery.send_reply(event, recipient, ai_response)

        if msg:
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=ai_response,
            )
            self.logger.info(f"[{recipient.username}] Отправлен ответ")

    async def _apply_status(
        self,
        dialog: orm.Dialog,
        recipient: orm.Recipient,
        new_status: enums.DialogStatus | None,
        messages: list[orm.Message],
    ):
        if new_status and new_status != dialog.status:
            old_status = dialog.status
            dialog.status = new_status

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
        recipient_messages = [
            m for m in messages if m.sender == enums.MessageSender.RECIPIENT
        ]

        if len(recipient_messages) < threshold:
            return False

        recent_messages = recipient_messages[-threshold:]

        normalized_texts = [
            m.text.strip().lower() if m.text else "" for m in recent_messages
        ]

        if len(set(normalized_texts)) == 1 and normalized_texts[0]:
            self.logger.warning(
                f"[{recipient.username}] Обнаружен спам: {threshold} одинаковых сообщений подряд"
            )
            return True

        return False

    async def _find_stuck_dialogs(self, min_age_minutes: int = 10) -> list[orm.Dialog]:
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

                if await self._process_system_messages_for_dialog(dialog):
                    continue

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
