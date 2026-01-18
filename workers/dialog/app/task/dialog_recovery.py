import asyncio
import random
from datetime import timedelta

from tortoise import timezone as tz

from app.common.models import enums, orm


async def find_stuck_dialogs(
    account_id: int, min_age_minutes: int = 10
) -> list[orm.Dialog]:
    """
    Находит зависшие диалоги по простым критериям:

    1. Статус в (INIT, ENGAGE, OFFER, CLOSING) - диалог активен
    2. finished_at IS NULL - диалог не завершен
    3. Последнее сообщение от RECIPIENT - ждем ответа
    4. Это сообщение старше min_age_minutes

    Args:
        account_id: ID аккаунта
        min_age_minutes: Минимальный возраст последнего сообщения

    Returns:
        Список зависших диалогов
    """

    # Статусы активных диалогов
    active_statuses = [
        enums.DialogStatus.INIT,
        enums.DialogStatus.ENGAGE,
        enums.DialogStatus.OFFER,
        enums.DialogStatus.CLOSING,
    ]

    # Получаем все активные незавершенные диалоги
    dialogs = await orm.Dialog.filter(
        account_id=account_id, status__in=active_statuses, finished_at__isnull=True
    ).prefetch_related("recipient", "messages")

    stuck_dialogs = []
    cutoff_time = tz.now() - timedelta(minutes=min_age_minutes)

    for dialog in dialogs:
        # Получаем последнее сообщение
        last_message = (
            await orm.Message.filter(dialog=dialog, ui_only=False)
            .order_by("-created_at")
            .first()
        )

        if not last_message:
            continue

        # Проверяем условия "зависания":
        # 1. Последнее от пользователя
        # 2. Достаточно старое
        if (
            last_message.sender == enums.MessageSender.RECIPIENT
            and last_message.created_at < cutoff_time
        ):
            stuck_dialogs.append(dialog)

    return stuck_dialogs


async def check_and_recover_stuck_dialogs(
    manager,  # DialogManager instance
    min_age_minutes: int = 10,
) -> int:
    """
    Проверяет и восстанавливает зависшие диалоги

    Args:
        manager: Экземпляр DialogManager
        min_age_minutes: Минимальный возраст для считания зависшим

    Returns:
        Количество восстановленных диалогов
    """

    stuck_dialogs = await find_stuck_dialogs(
        manager.account.id, min_age_minutes=min_age_minutes
    )

    if not stuck_dialogs:
        return 0

    manager.logger.warning(
        f"🔄 Обнаружено {len(stuck_dialogs)} зависших диалогов (без ответа > {min_age_minutes} мин)"
    )

    recovered = 0

    for dialog in stuck_dialogs:
        try:
            recipient = dialog.recipient

            manager.logger.info(
                f"🔧 Восстановление диалога {dialog.id} с @{recipient.username} "
                f"(статус: {dialog.status.value})"
            )

            # Получаем ВСЕ сообщения для контекста
            messages = await orm.Message.filter(dialog=dialog, ui_only=False).order_by(
                "created_at"
            )

            if not messages:
                continue

            # Генерируем ответ через стандартный механизм
            should_continue = await manager._generate_and_send_response(
                event=None,  # Передаем None, т.к. реального события нет
                dialog=dialog,
                recipient=recipient,
                messages=messages,
            )

            if should_continue:
                # Если диалог должен продолжаться - запускаем ожидание
                asyncio.create_task(
                    manager.start_waiting_for_first_reply(dialog, recipient)
                )

            recovered += 1

            # Задержка между восстановлениями
            await asyncio.sleep(random.randint(3, 7))

        except Exception as e:
            manager.logger.error(f"Ошибка при восстановлении диалога {dialog.id}: {e}")
            import traceback

            manager.logger.error(traceback.format_exc())
            continue

    if recovered > 0:
        manager.logger.info(
            f"✅ Успешно восстановлено {recovered} из {len(stuck_dialogs)} диалогов"
        )

    return recovered


async def get_stuck_dialogs_report(account_id: int) -> dict:
    """
    Получает детальный отчет о зависших диалогах
    Полезно для мониторинга и отладки

    Returns:
        Словарь с аналитикой по зависшим диалогам
    """

    stuck_dialogs = await find_stuck_dialogs(account_id, min_age_minutes=10)

    if not stuck_dialogs:
        return {"total": 0, "dialogs": []}

    report_dialogs = []

    for dialog in stuck_dialogs:
        last_message = (
            await orm.Message.filter(dialog=dialog, ui_only=False)
            .order_by("-created_at")
            .first()
        )
        if last_message:
            age_minutes = (tz.now() - last_message.created_at).total_seconds() / 60

            report_dialogs.append(
                {
                    "dialog_id": dialog.id,
                    "recipient_username": dialog.recipient.username,
                    "status": dialog.status.value,
                    "last_message_text": last_message.text[:50]
                    if last_message.text
                    else "",
                    "age_minutes": round(age_minutes, 1),
                    "started_at": dialog.started_at.isoformat(),
                }
            )

    return {
        "total": len(stuck_dialogs),
        "dialogs": sorted(report_dialogs, key=lambda x: x["age_minutes"], reverse=True),
    }
