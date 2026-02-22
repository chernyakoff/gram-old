import asyncio
from datetime import timedelta
from typing import Literal, cast

from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient, types
from telethon.errors import TimeoutError
from telethon.events import NewMessage
from telethon.tl.types import (
    KeyboardButton,
    ReplyInlineMarkup,
    ReplyKeyboardMarkup,
)
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from models import orm
from utils.account import AccountUtil
from utils.logger import StreamLogger
from utils.proxy_pool import ProxyPool
from workers.base.client import hatchet

PREMIUM_BOT = "PremiumBot"

# Настройка шагов кнопок по позиции (row_index, col_index)
AUTO_STOP_POSITIONS = [
    (0, 0),  # Подтверждение отмены подписки
    (0, 0),  # Выбор причины отказа
]

# Таймаут на случай зависания (секунды)
MAX_WAIT_SECONDS = 60


class StopPremiumIn(BaseModel):
    account_id: int


async def stop_premium_inline(
    client: TelegramClient, logger: StreamLogger
) -> Literal["error", "success", "noop", "no_premium"]:
    """
    Disable recurring in an already-connected session without disconnecting the client.

    This is used from long-running tasks (e.g. dialog) where the account may stay busy for hours,
    and scheduling the standalone `stop-premium` task would be delayed indefinitely.
    """
    nothing_to_stop_markers = (
        "Nothing to stop, recurring payments are already disabled for this account.",
        "Нечего отключать",
        "уже отключ",
    )

    me = await client.get_me()
    me = cast(types.User, me)
    if not me.premium:
        await logger.info("Premium отсутствует на аккаунте: отменять нечего")
        return "no_premium"

    steps_done = 0
    try:
        async with client.conversation("@PremiumBot", timeout=20) as conv:  # type: ignore
            await conv.send_message("/stop")

            # We expect a short chain of bot prompts with keyboards.
            for _ in range(8):
                msg = await conv.get_response()
                text = getattr(msg, "message", None) or ""
                await logger.info(text)

                if text and any(m in text for m in nothing_to_stop_markers):
                    await logger.info(
                        "Nothing to stop: recurring уже отключен для этого аккаунта"
                    )
                    return "noop"

                mk = getattr(msg, "reply_markup", None)
                if mk and isinstance(mk, (ReplyKeyboardMarkup, ReplyInlineMarkup)):
                    clicked = False
                    for ri, ci in AUTO_STOP_POSITIONS:
                        try:
                            await msg.click(ri, ci)
                            await logger.info(f"Нажата кнопка [{ri},{ci}]")
                            steps_done += 1
                            clicked = True
                            break
                        except Exception:
                            continue
                    if clicked:
                        continue
                    # keyboard exists but we couldn't click expected positions
                    await logger.warning(
                        "Не удалось нажать кнопку PremiumBot по ожидаемой позиции"
                    )
                    return "error"

                # no keyboard -> chain likely finished
                return "success" if steps_done > 0 else "error"

        return "success" if steps_done > 0 else "error"
    except TimeoutError:
        await logger.warning("Timeout: PremiumBot не ответил вовремя")
        return "error"
    except Exception as e:
        await logger.error(f"stop_premium_inline error: {e}")
        return "error"


async def _stop_premium(
    client: TelegramClient, logger: StreamLogger
) -> Literal["error", "success", "noop", "no_premium"]:
    finished = False  # флаг завершения цепочки
    steps_done = 0  # количество успешно пройденных шагов
    noop = False  # PremiumBot ответил "нечего отключать" (уже отключено)

    nothing_to_stop_markers = (
        "Nothing to stop, recurring payments are already disabled for this account.",
        "Нечего отключать",  # на случай локализации
        "уже отключ",  # "уже отключены/отключено"
    )

    async def debug_keyboard(msg):
        mk = msg.reply_markup
        if not mk:
            print("Клавиатуры нет")
            return
        if isinstance(mk, ReplyInlineMarkup):
            print("== InlineKeyboard ==")
            for ri, row in enumerate(mk.rows):
                for ci, btn in enumerate(row.buttons):
                    print(f"[{ri},{ci}] {getattr(btn, 'text', None)}")
        elif isinstance(mk, ReplyKeyboardMarkup):
            print("== ReplyKeyboard ==")
            for ri, row in enumerate(mk.rows):
                texts = [
                    btn.text for btn in row.buttons if isinstance(btn, KeyboardButton)
                ]
                print(f"[{ri}] {texts}")
        else:
            print(f"Неизвестный тип клавиатуры: {type(mk)}")

    @client.on(NewMessage(from_users="@PremiumBot"))
    async def handler(event):
        nonlocal finished, steps_done, noop
        try:
            msg = event.message
            await logger.info(msg.message)

            # await debug_keyboard(msg)
            if msg.message and any(m in msg.message for m in nothing_to_stop_markers):
                # Это корректный исход: recurring уже отключен.
                await logger.info(
                    "Nothing to stop: recurring уже отключен для этого аккаунта"
                )
                noop = True
                finished = True
                await client.disconnect()  # type: ignore
                return

            mk = msg.reply_markup
            if mk and isinstance(mk, (ReplyKeyboardMarkup, ReplyInlineMarkup)):
                # Жёстко нажимаем кнопки по позиции
                for pos in AUTO_STOP_POSITIONS:
                    ri, ci = pos
                    try:
                        await msg.click(ri, ci)
                        await logger.info(f"Нажата кнопка [{ri},{ci}]")
                        steps_done += 1
                        return
                    except Exception:
                        continue
            else:
                # клавиатуры нет → цепочка завершена
                await logger.info("Цепочка сообщений завершена, отключаемся")
                finished = True
                await client.disconnect()  # type: ignore
        except Exception as e:
            await logger.error(f"Ошибка в обработчике: {e}")

    async def monitor_timeout():
        nonlocal finished
        for _ in range(MAX_WAIT_SECONDS):
            if finished:
                return
            await asyncio.sleep(1)
        if not finished:
            await logger.warning(
                f"Таймаут {MAX_WAIT_SECONDS}s: отключаем клиента принудительно"
            )
            await client.disconnect()  # type: ignore

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await logger.error("Вылетел из сессии")
            return "error"

        me = await client.get_me()
        me = cast(types.User, me)
        if not me.premium:  # type: ignore
            await logger.info("Premium отсутствует на аккаунте: отменять нечего")
            return "no_premium"

        await client.send_message("@PremiumBot", "/stop")

        await asyncio.gather(client.run_until_disconnected(), monitor_timeout())  # type: ignore

        # После завершения цепочки определяем результат
        if noop:
            return "noop"
        return "success" if steps_done > 0 else "error"

    except Exception as e:
        await logger.error(f"Ошибка в основном блоке: {e}")
        return "error"

    finally:
        await client.disconnect()  # type: ignore


@hatchet.task(
    name="stop-premium",
    input_validator=StopPremiumIn,
    execution_timeout=timedelta(minutes=3),
    schedule_timeout=timedelta(minutes=3),
)
async def stop_premium(input: StopPremiumIn, ctx: Context):
    orm_account = await orm.Account.get(id=input.account_id).prefetch_related("proxy")
    if orm_account.busy is True:
        run_at = tz.now() + timedelta(minutes=10)
        schedule = stop_premium.schedule(
            run_at=run_at, input=StopPremiumIn(account_id=input.account_id)
        )
        ctx.log(f"scheduled stop-premium: {schedule.id}")
        return

    await asyncio.sleep(2)
    logger = StreamLogger(ctx)

    account_util = AccountUtil.from_orm(orm_account)
    pool = ProxyPool(orm_account.user_id)

    proxy = await pool.verify_proxy(orm_account)
    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    client = account_util.create_client(proxy)
    orm_account.busy = True
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy", "updated_at"])

    try:
        status = await _stop_premium(client, logger)
        if status == "no_premium":
            # Синхронизация: premium реально отсутствует (даже если в БД было иначе).
            orm_account.premium = False
            orm_account.premiumed_at = None  # type: ignore
            # Поле булевое (не nullable) в текущей модели, поэтому "сбрасываем" в False.
            orm_account.premium_stopped = False
            await logger.info("Premium отсутствует: сбрасываем флаги в БД и завершаем")
        elif status == "error":
            await logger.error("Не удалось отключить подписку")
            # Не "перекрашиваем" premium_stopped в False на любых ошибках:
            # мы не можем надёжно определить, включены ли recurring-платежи.
        else:
            # success/noop: recurring отключен, premium может оставаться активным до конца периода.
            await logger.success("Recurring платежи отключены")
            orm_account.premium_stopped = True
    except Exception as e:
        # Аналогично: на исключениях не трогаем premium_stopped, чтобы не скатывать UI в "жёлтую".
        await logger.error(f"Ошибка stop-premium: {e}")
    finally:
        orm_account.busy = False
        async with in_transaction() as conn:
            await orm_account.save(
                using_db=conn,
                update_fields=[
                    "busy",
                    "premium",
                    "premiumed_at",
                    "premium_stopped",
                    "updated_at",
                ],
            )
