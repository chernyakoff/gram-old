import asyncio
import json
from typing import Literal, Optional, cast

import aiohttp
from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient, types
from telethon.events import NewMessage
from telethon.sessions import StringSession
from telethon.tl.functions.payments import GetPaymentFormRequest, SendPaymentFormRequest
from telethon.tl.types import (
    DataJSON,
    InputInvoiceMessage,
    InputPaymentCredentials,
    KeyboardButton,
    KeyboardButtonCallback,
    MessageMediaInvoice,
    ReplyInlineMarkup,
    ReplyKeyboardMarkup,
)
from telethon.tl.types.payments import PaymentVerificationNeeded
from telethon.types import Message
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import orm
from app.common.utils.account import AccountUtil
from app.common.utils.proxy_pool import ProxyPool
from app.tasks.accounts.exceptions import SessionExpiredError
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


class StopPremiumOut(BaseModel):
    status: Literal["error", "success"]
    message: Optional[str] = None


async def cancel_premium(client: TelegramClient) -> str:
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
            print("\n=== Новое сообщение от @PremiumBot ===")
            print(msg.message)

            await debug_keyboard(msg)

            mk = msg.reply_markup
            if mk and isinstance(mk, (ReplyKeyboardMarkup, ReplyInlineMarkup)):
                # Жёстко нажимаем кнопки по позиции
                for pos in AUTO_STOP_POSITIONS:
                    ri, ci = pos
                    try:
                        await msg.click(ri, ci)
                        print(f"Нажата кнопка [{ri},{ci}]")
                        steps_done += 1
                        return
                    except Exception:
                        continue
            else:
                # клавиатуры нет → цепочка завершена
                print("Цепочка сообщений завершена, отключаемся")
                finished = True
                await client.disconnect()  # type: ignore
        except Exception as e:
            print("Ошибка в обработчике:", e)

    async def monitor_timeout():
        nonlocal finished
        for _ in range(MAX_WAIT_SECONDS):
            if finished:
                return
            await asyncio.sleep(1)
        if not finished:
            print(f"Таймаут {MAX_WAIT_SECONDS}s: отключаем клиента принудительно")
            await client.disconnect()  # type: ignore

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Сессия не авторизована")
            return "error"

        await client.send_message("@PremiumBot", "/stop")

        await asyncio.gather(client.run_until_disconnected(), monitor_timeout())  # type: ignore

        # После завершения цепочки определяем результат
        return "success" if steps_done > 0 else "error"

    except Exception as e:
        print("Ошибка в основном блоке:", e)
        return "error"

    finally:
        await client.disconnect()  # type: ignore
        print("Сессия завершена")


@hatchet.task(name="stop-premium", input_validator=StopPremiumIn)
async def buy_premium(input: StopPremiumIn, ctx: Context) -> StopPremiumOut:
    logger = StreamLogger(ctx)

    orm_account = await orm.Account.get(id=input.account_id)

    return StopPremiumOut(status="success")
