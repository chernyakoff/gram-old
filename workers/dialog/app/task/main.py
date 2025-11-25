import asyncio
import random
from datetime import timedelta

from hatchet_sdk import ConcurrencyExpression, ConcurrencyLimitStrategy, Context
from pydantic import BaseModel
from telethon.types import User as TelethonUser
from tortoise import Tortoise
from tortoise import timezone as tz
from tortoise.expressions import Subquery
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.functions import generate_message
from app.task.manager import DialogManager
from app.task.telegram_service import FrozenError, SpamBlockedError
from app.utils.account import AccountUtil
from app.utils.account_limiter import AccountLimiter
from app.utils.logger import Logger
from app.utils.proxy_pool import ProxyPool

# Максимальное время на случай если что-то пойдет не так
MAX_SESSION_HOURS = 6


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]
    key: str


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


@hatchet.task(
    name="dialog",
    input_validator=DialogIn,
    execution_timeout=timedelta(hours=MAX_SESSION_HOURS),
    schedule_timeout=timedelta(hours=MAX_SESSION_HOURS),
    concurrency=ConcurrencyExpression(
        expression="input.key",
        max_runs=1,
        limit_strategy=ConcurrencyLimitStrategy.CANCEL_NEWEST,
    ),
)
async def dialog_task(input: DialogIn, ctx: Context):
    logger = Logger(ctx)
    account = await orm.Account.get(id=input.account_id).prefetch_related("user")
    if not account:
        return

    pool = ProxyPool(account.user_id)
    account_util = await AccountUtil.from_orm(account)

    client = None
    start_time = tz.now()
    end_time = start_time + timedelta(hours=MAX_SESSION_HOURS)
    stop_event = asyncio.Event()

    try:
        async with pool.proxy(
            account.country, timeout=30, account_id=account.id
        ) as proxy:
            client = account_util.create_client(proxy)

            try:
                # Подключение с таймаутом
                await asyncio.wait_for(client.connect(), timeout=30)
            except asyncio.TimeoutError:
                logger.error("Таймаут подключения клиента (30 сек)")
                await release_account(account, error="Client connect timeout")
                return
            except Exception as e:
                logger.error(f"Ошибка подключения клиента: {e}")
                # Специальная обработка для AuthKeyDuplicatedError
                if "used under two different IP" in str(e):
                    logger.error(
                        "⚠️ КРИТИЧНО: Сессия использована с другого IP! Деактивируем аккаунт."
                    )
                    account.active = False
                    account.status = enums.AccountStatus.EXITED
                    await account.save(update_fields=["active", "status"])
                await release_account(account, error=f"Connection error: {e}")
                return

            try:
                is_authorized = await asyncio.wait_for(
                    client.is_user_authorized(), timeout=10
                )
                if not is_authorized:
                    logger.error(f"Account {account.id} не авторизован")
                    await release_account(account, error="Account not authorized")
                    return
            except asyncio.TimeoutError:
                logger.error("Таймаут проверки авторизации")
                await release_account(account, error="Authorization check timeout")
                return

            logger.info(f"Account {account.id} подключен к Telegram")

            project = await orm.Project.get(id=account.project_id)  # type: ignore
            prompt = await orm.Prompt.get_or_none(project_id=account.project_id)  # type: ignore
            if not prompt:
                raise Exception(f"У юзера [{account.user_id}] отсутсвует промпт")

            limiter = AccountLimiter(account)

            # Создаём менеджер диалогов
            manager = DialogManager(
                client=client,
                project=project,
                prompt=prompt.to_dict(),
                account=account,
                logger=logger,
                stop_event=stop_event,
            )
            if await manager.telegram_service.is_frozen():
                raise FrozenError()

            muted_until = await manager.telegram_service.is_spamblock()
            if muted_until:
                raise SpamBlockedError(muted_until)

            manager.setup_event_handlers()

            # Проверяем старые диалоги на новые сообщения
            old_dialogs_with_messages = (
                await manager.check_old_dialogs_for_new_messages()
            )
            logger.info(
                f"Старых диалогов с новыми сообщениями: {old_dialogs_with_messages}"
            )

            # Отправляем первые сообщения новым получателям
            new_dialogs_started = 0
            first_message = generate_message(project.first_message)

            for recipient_id in input.recipients_id:
                recipient = await orm.Recipient.get(id=recipient_id)

                # Получаем entity
                entity = await manager.telegram_service.get_entity(recipient)
                if not entity:
                    continue

                manager.register_session_recipient(recipient.id)

                # Проверяем, не существует ли уже диалог
                dialog_exists = await orm.Dialog.get_or_none(recipient=recipient)
                if dialog_exists:
                    continue

                # Отправляем первое сообщение
                msg = await manager.telegram_service.send_message(
                    recipient, first_message
                )
                if not msg:
                    continue

                # Создаём диалог
                dialog = await orm.Dialog.create(
                    recipient=recipient,
                    status=enums.DialogStatus.INIT,
                    account_id=account.id,
                )

                if isinstance(entity, TelethonUser):
                    dialog.update_from_dict(
                        {
                            "recipient_peer_id": entity.id,
                            "recipient_access_hash": entity.access_hash,
                        }
                    )
                    await dialog.save()

                # Сохраняем сообщение
                await orm.Message.create(
                    dialog=dialog,
                    sender=enums.MessageSender.ACCOUNT,
                    tg_message_id=msg.id,
                    text=first_message,
                )

                await limiter.increment(enums.AccountAction.NEW_DIALOG)
                new_dialogs_started += 1

                # Запускаем ожидание ответа на первое сообщение
                asyncio.create_task(
                    manager.start_waiting_for_first_reply(dialog, recipient)
                )

                if stop_event.is_set() or tz.now() > end_time:
                    break

                # Задержка между отправками
                await asyncio.sleep(random.randint(60, 180))

            logger.info(f"Новых диалогов начато: {new_dialogs_started}")

            # Если не было ни новых диалогов, ни ответов в старых - сразу выключаемся
            if new_dialogs_started == 0 and old_dialogs_with_messages == 0:
                logger.info(
                    "🛑 Нет новых диалогов и нет ответов в старых - завершаем работу"
                )
                return  # finally сработает и disconnect будет вызван

            # Основной цикл - держим соединение пока есть активные диалоги
            logger.info(
                f"Account {account.id} вошёл в режим ожидания. "
                f"Активных диалогов: {manager.active_dialogs_count}"
            )

            # Периодически проверяем состояние
            last_check = tz.now()
            last_full_check = tz.now()
            CHECK_INTERVAL_SEC = 30
            FULL_CHECK_INTERVAL_SEC = 60

            while tz.now() < end_time and not stop_event.is_set():
                if not client.is_connected():
                    logger.error("Потеряно соединение, завершаем задачу")
                    await release_account(account, error="Connection lost")
                    return  # finally сработает

                # Каждые 30 секунд логируем состояние
                if (tz.now() - last_check).total_seconds() >= CHECK_INTERVAL_SEC:
                    logger.info(
                        f"Статус: активных_диалогов={manager.active_dialogs_count}, "
                        f"ожидающих_обработки={len(manager.waiting_dialogs)}"
                    )
                    last_check = tz.now()

                # Каждую минуту делаем полную проверку
                if (
                    tz.now() - last_full_check
                ).total_seconds() >= FULL_CHECK_INTERVAL_SEC:
                    await manager._check_and_stop_if_needed()
                    last_full_check = tz.now()

                await asyncio.sleep(10)

            if stop_event.is_set():
                logger.info(
                    f"Account {account.id} остановлен: "
                    f"все диалоги завершены или достигнут лимит"
                )
            else:
                logger.info(
                    f"Account {account.id} остановлен: "
                    f"истекло максимальное время сессии ({MAX_SESSION_HOURS}ч)"
                )

    except asyncio.TimeoutError:
        msg = "Прокси не ответил вовремя"
        logger.warning(msg)
        await release_account(account, error=msg)
        raise

    except FrozenError:
        logger.warning("Аккаунт заморожен")
        account.active = False
        account.status = enums.AccountStatus.FROZEN
        await account.save(update_fields=["status"])
        raise

    except SpamBlockedError as e:
        msg = f"Аккаунт попал в мут до {e.muted_until:%d.%m.%Y}"
        logger.warning(msg)
        account.active = False
        account.muted_until = e.muted_until
        account.status = enums.AccountStatus.MUTED
        await account.save(update_fields=["status", "muted_until", "active"])
        raise

    except Exception as e:
        msg = f"Неизвестная ошибка: {type(e).__name__}: {e}"
        logger.error(msg)
        import traceback

        logger.error(traceback.format_exc())
        await release_account(account, error=msg)
        raise

    finally:
        # КРИТИЧЕСКИ ВАЖНО: всегда отключаем клиента
        if client is not None:
            disconnect_attempts = 0
            max_disconnect_attempts = 3

            while disconnect_attempts < max_disconnect_attempts:
                try:
                    if client.is_connected():
                        logger.info(
                            f"Отключение клиента (попытка {disconnect_attempts + 1}/{max_disconnect_attempts})"
                        )
                        await asyncio.wait_for(client.disconnect(), timeout=10)  # type: ignore
                        logger.info("✅ Клиент корректно отключён")
                        break
                    else:
                        logger.info("Клиент уже был отключён")
                        break
                except asyncio.TimeoutError:
                    disconnect_attempts += 1
                    logger.warning(
                        f"Таймаут отключения клиента (попытка {disconnect_attempts})"
                    )
                    if disconnect_attempts >= max_disconnect_attempts:
                        logger.error("❌ Не удалось отключить клиента после 3 попыток")
                except Exception as e:
                    disconnect_attempts += 1
                    logger.error(
                        f"Ошибка при отключении клиента (попытка {disconnect_attempts}): {e}"
                    )
                    if disconnect_attempts >= max_disconnect_attempts:
                        logger.error("❌ Критическая ошибка отключения клиента")
                        # Последняя попытка - force disconnect
                        try:
                            await client.disconnect()  # type: ignore
                        except:
                            pass
                        break

                await asyncio.sleep(1)  # Пауза между попытками

        await release_account(account)
