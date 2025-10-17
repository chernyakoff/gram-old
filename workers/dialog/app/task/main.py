import asyncio
import random
from datetime import timedelta

from hatchet_sdk import Context
from pydantic import BaseModel
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.functions import generate_message
from app.task.manager import DialogManager
from app.utils.account import AccountUtil
from app.utils.account_limiter import AccountLimiter
from app.utils.logger import Logger
from app.utils.proxy_pool import ProxyPool

SESSION_LIFETIME_HOURS = 6


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]


async def release_account(account: orm.Account, error: str | None = None):
    """Освободить аккаунт, при ошибке сохранить last_error"""
    update_data = {
        "busy": False,
        "lease_expires_at": None,
        "worker_id": None,
        "last_attempt_at": tz.now(),
        "last_error": error,
    }

    account.update_from_dict(update_data)
    async with in_transaction():
        await account.save(update_fields=list(update_data.keys()))


@hatchet.durable_task(
    name="dialog",
    input_validator=DialogIn,
    execution_timeout=timedelta(hours=6),
    schedule_timeout=timedelta(hours=6),
)
async def dialog_task(input: DialogIn, ctx: Context):
    """Главная задача для работы с диалогами"""

    logger = Logger(ctx)
    account = await orm.Account.get(id=input.account_id).prefetch_related("user")

    # Аккаунт уже захвачен в heartbeat, не нужно acquire

    pool = ProxyPool(account.user_id)
    account_util = await AccountUtil.from_orm(account)

    client = None
    start_time = tz.now()
    end_time = start_time + timedelta(hours=SESSION_LIFETIME_HOURS)
    stop_event = asyncio.Event()

    try:
        async with pool.proxy(account.country, timeout=30) as proxy:
            client = account_util.create_client(proxy)
            await client.connect()

            if not await client.is_user_authorized():
                logger.error(f"Account {account.id} не авторизован")
                await release_account(account, error="Account not authorized")
                return

            logger.info(f"Account {account.id} подключен к Telegram")

            project = await orm.Project.get(id=account.project_id)  # type: ignore
            limiter = AccountLimiter(account)

            # Создаём менеджер диалогов
            manager = DialogManager(
                client, project, account, input.recipients_id, logger, stop_event
            )
            manager.setup_event_handlers()

            # Отправляем первые сообщения
            first_message = generate_message(project.first_message)

            for recipient_id in input.recipients_id:
                recipient = await orm.Recipient.get(id=recipient_id)

                # Получаем entity
                entity = await manager.telegram_service.get_entity(recipient)
                if not entity:
                    continue

                # Отправляем первое сообщение
                msg = await manager.telegram_service.send_message(
                    recipient, first_message
                )
                if not msg:
                    continue

                # Создаём диалог
                dialog, created = await orm.Dialog.get_or_create(
                    recipient=recipient, defaults={"status": enums.DialogStatus.INIT}
                )

                if created:
                    logger.info(f"[{recipient.username}] Создан диалог")

                # Сохраняем сообщение
                await orm.Message.create(
                    dialog=dialog,
                    sender=enums.MessageSender.ACCOUNT,
                    tg_message_id=msg.id,
                    text=first_message,
                )

                await limiter.increment(enums.AccountAction.NEW_DIALOG)

                if stop_event.is_set() or tz.now() > end_time:
                    break

                # Задержка между отправками
                await asyncio.sleep(random.randint(60, 180))

            # Основной цикл – держим соединение
            logger.info(f"Account {account.id} вошёл в режим ожидания сообщений")

            while tz.now() < end_time and not stop_event.is_set():
                if not client.is_connected():
                    logger.warning("Потеряно соединение, переподключаемся...")
                    await client.connect()
                await asyncio.sleep(30)  # ping каждые 30 сек

            if stop_event.is_set():
                logger.info(f"Account {account.id} остановлен: достигнут лимит")
            else:
                logger.info(f"Account {account.id} остановлен: истекло время сессии")

    except asyncio.TimeoutError:
        msg = "Прокси не ответил вовремя"
        logger.warning(msg)
        await release_account(account, error=msg)

    except Exception as e:
        msg = f"Неизвестная ошибка: {type(e).__name__}: {e}"
        logger.error(msg)
        import traceback

        logger.error(traceback.format_exc())
        await release_account(account, error=msg)

    finally:
        try:
            if client and client.is_connected():
                await client.disconnect()  # type: ignore
                logger.info("Клиент корректно отключён")
        except Exception as e:
            logger.error(f"Ошибка при отключении клиента: {e}")

        # Если не было ошибки выше – делаем нормальный release
        if not account.last_error:
            await release_account(account)
