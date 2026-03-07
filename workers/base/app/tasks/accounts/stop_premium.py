import asyncio
from datetime import timedelta
from typing import Literal, Optional

from hatchet_sdk import (
    ConcurrencyExpression,
    ConcurrencyLimitStrategy,
    Context,
)
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.tl.types import (
    KeyboardButton,
    ReplyInlineMarkup,
    ReplyKeyboardMarkup,
)
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import orm
from app.common.utils.account import AccountUtil
from app.tasks.accounts.pool_selector import build_pool, is_mobile_pool
from app.utils.stream_logger import StreamLogger

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
    user_id: int
    concurrency_key: str


async def _stop_premium(
    client: TelegramClient, logger: StreamLogger
) -> Literal["error", "success"]:
    finished = False  # флаг завершения цепочки
    steps_done = 0  # количество успешно пройденных шагов

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
        nonlocal finished, steps_done
        try:
            msg = event.message
            await logger.info(msg.message)

            # await debug_keyboard(msg)

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

        await client.send_message("@PremiumBot", "/stop")

        await asyncio.gather(client.run_until_disconnected(), monitor_timeout())  # type: ignore

        # После завершения цепочки определяем результат
        return "success" if steps_done > 0 else "error"

    except Exception as e:
        await logger.error(f"Ошибка в основном блоке: {e}")
        return "error"

    finally:
        await client.disconnect()  # type: ignore


async def _stop_premium_impl(input: StopPremiumIn, ctx: Context):
    await asyncio.sleep(2)
    logger = StreamLogger(ctx)
    orm_account = await orm.Account.get(id=input.account_id).prefetch_related("proxy")
    account_util = AccountUtil.from_orm(orm_account)
    pool = await build_pool(input.user_id)

    proxy = await pool.verify_proxy(orm_account)
    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    client = account_util.create_client(proxy)
    orm_account.busy = True
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy"])

    status = await _stop_premium(client, logger)
    if status == "error":
        await logger.error("Не удалось отключить подписку")
        orm_account.premium_stopped = False
    else:
        await logger.success("Подписка успешно отключена")
        orm_account.premium_stopped = True

    orm_account.busy = False
    orm_account.premium_stopped = True
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy", "premium_stopped"])
    if proxy and is_mobile_pool(pool):
        await pool.release_proxy_lock(proxy)


@hatchet.task(
    name="stop-premium",
    input_validator=StopPremiumIn,
    execution_timeout=timedelta(hours=1),
    schedule_timeout=timedelta(hours=1),
)
async def stop_premium(input: StopPremiumIn, ctx: Context):
    await _stop_premium_impl(input, ctx)


@hatchet.task(
    name="stop-premium-mp",
    input_validator=StopPremiumIn,
    execution_timeout=timedelta(hours=1),
    schedule_timeout=timedelta(hours=1),
    concurrency=ConcurrencyExpression(
        expression="input.concurrency_key",
        max_runs=1,
        limit_strategy=ConcurrencyLimitStrategy.GROUP_ROUND_ROBIN,
    ),
)
async def stop_premium_mp(input: StopPremiumIn, ctx: Context):
    await _stop_premium_impl(input, ctx)
