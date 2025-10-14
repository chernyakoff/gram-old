import asyncio
import random
from datetime import timedelta
from functools import partial

from hatchet_sdk import Context
from openai import AsyncOpenAI
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    PeerFloodError,
    RPCError,
    SlowModeWaitError,
    UserDeactivatedBanError,
    UserDeactivatedError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.events import NewMessage
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.functions import generate_message
from app.config import config
from app.utils.account import AccountUtil
from app.utils.account_limiter import AccountLimiter
from app.utils.logger import Logger
from app.utils.proxy_pool import ProxyPool

SESSION_LIFETIME_HOURS = 6

""" 
TODO: сделать возможность получать recipients самому если в переданных ошбика
"""


params = {
    "api_key": config.openai.api_key,
    "timeout": config.openai.timeout,
}
if config.openai.base_url:
    params["base_url"] = config.openai.base_url


openai_client = AsyncOpenAI(**params)


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]


async def acquire_account(account: orm.Account, worker_id: str):
    """Пометить аккаунт занятым и установить lease."""
    update_data = {
        "busy": True,
        "worker_id": worker_id,
        "lease_expires_at": tz.now() + timedelta(hours=SESSION_LIFETIME_HOURS),
        "last_attempt_at": tz.now(),
        "last_error": None,
    }
    account.update_from_dict(update_data)
    async with in_transaction():
        await account.save(update_fields=list(update_data.keys()))


async def release_account(account: orm.Account, error: str | None = None):
    """Освободить аккаунт, при ошибке сохранить last_error."""
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


async def get_entity(client: TelegramClient, recipient: orm.Recipient, logger: Logger):
    recipient.attempts += 1
    recipient.last_attempt_at = tz.now()

    try:
        entity = await client.get_entity(recipient.username)
        recipient.status = enums.RecipientStatus.PROCESSING
        recipient.last_error = None  # type: ignore
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        return entity

    except FloodWaitError as e:
        recipient.last_error = f"FloodWait: {e.seconds}s"
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] FloodWait: ждать {e.seconds} сек")
        await asyncio.sleep(e.seconds)
        return None

    except (UsernameNotOccupiedError, UsernameInvalidError):
        recipient.last_error = "Username invalid or not occupied"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] Username не существует")
        return None

    except (UserDeactivatedError, UserDeactivatedBanError):
        recipient.last_error = "User deactivated or banned"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] Аккаунт деактивирован")
        return None

    except RPCError as e:
        recipient.last_error = f"RPCError: {e.__class__.__name__}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] RPCError: {e}")
        return None

    except Exception as e:
        recipient.last_error = f"Unexpected error: {e}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.error(f"[{recipient.username}] Неизвестная ошибка: {e}")
        return None


async def send_message(
    client: TelegramClient, recipient: orm.Recipient, logger: Logger, text: str
):
    recipient.attempts += 1
    recipient.last_attempt_at = tz.now()

    try:
        msg = await client.send_message(recipient.username, text)
        recipient.status = enums.RecipientStatus.SENT
        recipient.last_error = None  # type: ignore
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        return msg

    except FloodWaitError as e:
        recipient.last_error = f"FloodWait: {e.seconds}s"
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] FloodWait {e.seconds}s — ждём...")
        await asyncio.sleep(e.seconds)
        return None

    except SlowModeWaitError as e:
        recipient.last_error = f"SlowModeWait: {e.seconds}s"
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] SlowMode {e.seconds}s — ждём...")
        await asyncio.sleep(e.seconds)
        return None

    except ChatWriteForbiddenError:
        recipient.last_error = "Cannot send messages to this chat"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] Писать в чат запрещено")
        return None

    except PeerFloodError:
        recipient.last_error = "PeerFlood: слишком много исходящих"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.error(f"[{recipient.username}] PeerFlood — аккаунт перегружен")
        return None

    except RPCError as e:
        recipient.last_error = f"RPCError: {e.__class__.__name__}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.warning(f"[{recipient.username}] RPCError: {e}")
        return None

    except Exception as e:
        recipient.last_error = f"Unexpected: {e}"
        recipient.status = enums.RecipientStatus.FAILED
        await recipient.save(
            update_fields=["attempts", "last_attempt_at", "status", "last_error"]
        )
        if logger:
            logger.error(
                f"[{recipient.username}] Неизвестная ошибка при send_message: {e}"
            )
        return None


async def get_ai_response(
    project_prompt: str, dialog_messages: list[orm.Message], logger: Logger
) -> str | None:
    history = []
    for msg in dialog_messages:
        role = "assistant" if msg.sender == enums.MessageSender.ACCOUNT else "user"
        history.append({"role": role, "content": msg.text})

    messages = [{"role": "system", "content": project_prompt}] + history
    try:
        completion = await openai_client.chat.completions.create(
            model=config.openai.model,
            messages=messages,  # type: ignore
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(str(e))


async def get_ai_response_with_status(
    project_prompt: str, dialog_messages: list[orm.Message], logger: Logger
) -> tuple[str | None, enums.DialogStatus | None]:
    """Возвращает ответ и новый статус диалога"""

    history = []
    for msg in dialog_messages:
        role = "assistant" if msg.sender == enums.MessageSender.ACCOUNT else "user"
        history.append({"role": role, "content": msg.text})

    system_prompt = f"""{project_prompt}

ВАЖНО: После каждого ответа укажи статус диалога на отдельной строке в формате:
STATUS: [init|engage|offer|close]

Критерии:
- init: первое взаимодействие
- engage: получатель проявляет интерес, задает вопросы
- offer: сделано конкретное предложение
- close: диалог завершен (отказ, договоренность, потеря интереса)
"""

    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        completion = await openai_client.chat.completions.create(
            model=config.openai.model,
            messages=messages,  # type: ignore
        )
        response = completion.choices[0].message.content

        if not response:
            return None, None

        # Парсим статус
        status = None
        text = response

        if "STATUS:" in response:
            parts = response.split("STATUS:")
            text = parts[0].strip()
            status_str = parts[1].strip().lower()

            try:
                status = enums.DialogStatus(status_str)
            except ValueError:
                logger.warning(f"Неизвестный статус от AI: {status_str}")

        return text, status

    except Exception as e:
        logger.error(f"Ошибка get_ai_response: {e}")
        return None, None


async def check_and_stop_if_needed(
    project: orm.Project, stop_event: asyncio.Event, logger: Logger
):
    """Проверяет условия для остановки task"""

    # Подсчитываем активные диалоги
    active_dialogs = await orm.Dialog.filter(
        recipient__project_id=project.id, status__not_in=[enums.DialogStatus.CLOSE]
    ).count()

    closed_dialogs = await orm.Dialog.filter(
        recipient__project_id=project.id, status=enums.DialogStatus.CLOSE
    ).count()

    logger.info(
        f"Статус диалогов: активных={active_dialogs}, закрытых={closed_dialogs}"
    )

    # Если все диалоги закрыты, останавливаем task
    if active_dialogs == 0 and closed_dialogs > 0:
        logger.info("Все диалоги завершены, останавливаем task")
        stop_event.set()
        return

    # Или если есть лимит на общее количество закрытых диалогов
    if (
        hasattr(project, "out_daily_limit")
        and closed_dialogs >= project.out_daily_limit
    ):
        logger.info(f"Достигнут лимит закрытых диалогов: {closed_dialogs}")
        stop_event.set()
        return


async def on_new_message(
    event: NewMessage.Event,
    client: TelegramClient,
    project: orm.Project,
    logger: Logger,
    stop_event: asyncio.Event,
):
    try:
        sender = await event.get_sender()
        if not sender.username:
            return
        text = event.raw_text

        recipient = await orm.Recipient.get_or_none(username=sender.username)
        if not recipient:
            return

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

        logger.info(f"Получено новое сообщение от {recipient.username}")

        # Получаем историю диалога
        messages = await orm.Message.filter(dialog=dialog).order_by("created_at")

        message_count = len(messages)
        if message_count >= project.dialog_limit:
            dialog.status = enums.DialogStatus.CLOSE
            await dialog.save()
            logger.info(
                f"Диалог с {recipient.username} закрыт: достигнут лимит {project.dialog_limit} сообщений"
            )
            # Проверяем, нужно ли останавливать весь task
            await check_and_stop_if_needed(project, stop_event, logger)
            return

        # Генерируем ответ от AI
        async with client.action(event.chat_id, "typing"):  # type: ignore
            try:
                ai_response, new_status = await asyncio.wait_for(
                    get_ai_response_with_status(project.prompt, messages, logger),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                logger.warning(f"OpenAI timeout для {recipient.username}")
                return

            if not ai_response:
                return

        if new_status and new_status != dialog.status:
            old_status = dialog.status
            dialog.status = new_status
            await dialog.save()
            logger.info(f"Статус диалога изменен: {old_status} -> {new_status}")

            # Если диалог закрыт, проверяем условия остановки
            if new_status == enums.DialogStatus.CLOSE:
                await check_and_stop_if_needed(project, stop_event, logger)

        msg = await send_message(client, recipient, logger, ai_response)
        if msg:
            await orm.Message.create(
                dialog=dialog,
                sender=enums.MessageSender.ACCOUNT,
                tg_message_id=msg.id,
                text=ai_response,
            )

            logger.info(f"Отправлен ответ {recipient.username}")
            await check_and_stop_if_needed(project, stop_event, logger)

    except Exception as e:
        logger.error(f"Ошибка в on_new_message: {e}")


@hatchet.durable_task(
    name="dialog",
    input_validator=DialogIn,
    execution_timeout=timedelta(hours=6),
    schedule_timeout=timedelta(hours=6),
)
async def dialog_task(input: DialogIn, ctx: Context):
    logger = Logger(ctx)
    account = await orm.Account.get(id=input.account_id).prefetch_related("user")

    await acquire_account(account, f"{ctx.worker.id()}")

    pool = ProxyPool(account.user_id)
    account_util = await AccountUtil.from_orm(account)

    client: TelegramClient | None = None
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

            first_message = generate_message(project.first_message)

            client.add_event_handler(
                partial(
                    on_new_message,
                    client=client,
                    project=project,
                    logger=logger,
                    stop_event=stop_event,
                ),
                NewMessage(),
            )

            for recipient_id in input.recipients_id:
                recipient = await orm.Recipient.get(id=recipient_id)
                entity = await get_entity(client, recipient, logger)
                if not entity:
                    continue

                msg = await send_message(client, recipient, logger, first_message)
                if not msg:
                    continue
                dialog, _ = await orm.Dialog.get_or_create(
                    recipient=recipient, defaults={"status": enums.DialogStatus.INIT}
                )

                await orm.Message.create(
                    dialog=dialog,
                    sender=enums.MessageSender.ACCOUNT,
                    tg_message_id=msg.id,
                    text=first_message,
                )

                await limiter.increment(enums.AccountAction.NEW_DIALOG)
                if stop_event.is_set() or tz.now() > end_time:
                    break

                await asyncio.sleep(random.randint(60, 180))

            # Основной цикл — просто держим соединение
            while tz.now() < end_time and not stop_event.is_set():
                if not client.is_connected():
                    logger.warning("Потеряно соединение, пытаемся переподключиться...")
                    await client.connect()
                await asyncio.sleep(30)  # ping каждые 30 сек

            if stop_event.is_set():
                logger.info(f"Account {account.id} остановлен по достижению лимитов")
            else:
                logger.info(f"Account {account.id} завершил работу по таймауту")

    except asyncio.TimeoutError:
        msg = "Прокси не ответил вовремя"
        logger.warning(msg)
        await release_account(account, error=msg)

    except Exception as e:
        msg = f"Неизвестная ошибка: {type(e).__name__}: {e}"
        logger.error(msg)
        await release_account(account, error=msg)

    finally:
        try:
            if client and client.is_connected():
                await client.disconnect()  # type: ignore
                logger.info("Клиент корректно отключён")
        except Exception as e:
            logger.error(f"Ошибка при отключении клиента: {e}")

        # если не было ошибки выше — делаем нормальный release
        if not account.last_error:
            await release_account(account)
