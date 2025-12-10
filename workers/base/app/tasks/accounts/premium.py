import asyncio
import json
from typing import Literal, Optional, cast

import aiohttp
from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import types
from telethon.tl.functions.payments import GetPaymentFormRequest, SendPaymentFormRequest
from telethon.tl.types import (
    DataJSON,
    InputInvoiceMessage,
    InputPaymentCredentials,
    MessageMediaInvoice,
)
from telethon.tl.types.payments import PaymentVerificationNeeded
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import orm
from app.common.utils.account import AccountUtil
from app.common.utils.proxy_pool import ProxyPool
from app.tasks.accounts.exceptions import SessionExpiredError
from app.utils.stream_logger import StreamLogger

PREMIUM_BOT = "PremiumBot"


class CardDetails(BaseModel):
    number: str
    month: int
    year: int
    cvv: str


class BuyPremiumIn(BaseModel):
    account_id: int
    card: CardDetails


class BuyPremiumOut(BaseModel):
    status: Literal["error", "success"]
    message: Optional[str] = None
    verification_url: Optional[str] = None


async def tokenize_card(public_token: str, card: CardDetails):
    card_info = {
        "card": {
            "number": card.number,
            "expiration_month": f"{int(card.month):02d}",  # 7 -> "07"
            "expiration_year": str(card.year)[-2:],  # 2025 -> "25"
            "security_code": card.cvv,
        }
    }

    tokenization_url = "https://tgb.smart-glocal.com/cds/v1/tokenize/card"
    headers = {
        "X-PUBLIC-TOKEN": public_token,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            tokenization_url, json=card_info, headers=headers
        ) as resp:
            raw_text = (
                await resp.text()
            )  # читаем ответ без попытки парсинга, чтобы видеть реальное
            print("STATUS:", resp.status)
            print("HEADERS:", resp.headers)
            print("RAW RESPONSE:", raw_text)

            if resp.status != 200:
                print("❌ Server returned non-200 response, stopping.")
                return False, None

            try:
                data = await resp.json()
            except Exception as e:
                print("❌ JSON decode error:", e)
                return False, None

            print("✅ Parsed JSON:", data)

            token = data.get("data", {}).get("token")
            if not token:
                print("❌ Token not found in response")
                return False, None

            payment_json = json.dumps({"token": token, "type": "card"})
            return True, payment_json


@hatchet.task(name="buy-premium", input_validator=BuyPremiumIn)
async def buy_premium(input: BuyPremiumIn, ctx: Context) -> BuyPremiumOut:
    logger = StreamLogger(ctx)
    card = input.card

    orm_account = await orm.Account.get(id=input.account_id).prefetch_related("proxy")

    user_id = orm_account.user_id

    pool = ProxyPool(user_id)
    proxy = await pool.verify_proxy(orm_account)
    if not proxy:
        await logger.error("отсутствуют валидные прокси")
        return BuyPremiumOut(status="error", message="отсутствуют валидные прокси")

    account = AccountUtil.from_orm(orm_account)
    orm_account.busy = True
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy"])

    client = account.create_client(proxy)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise SessionExpiredError(account.phone)

        me = await client.get_me()
        me = cast(types.User, me)
        if me.premium:
            raise Exception("На этом аккаунте уже есть премиум")

        # получаем invoice message
        await client.send_message(PREMIUM_BOT, "/start")
        await asyncio.sleep(2)
        messages = await client.get_messages(PREMIUM_BOT, limit=4)
        if not messages:
            raise Exception("PremiumBot не ответил на /start")

        if isinstance(messages, types.Message):
            messages = [messages]

        invoice_msg = next(
            (m for m in messages if isinstance(m.media, MessageMediaInvoice)),
            None,
        )

        if not invoice_msg:
            raise Exception("Не найдено сообщение с invoice")

        # получаем public_token
        public_token = None
        peer = await client.get_input_entity(invoice_msg.peer_id)
        invoice = InputInvoiceMessage(peer=peer, msg_id=invoice_msg.id)
        form_info = await client(GetPaymentFormRequest(invoice=invoice))  # type: ignore
        native = getattr(form_info, "native_params", None)
        if native:
            # Это telethon.tl.types.DataJSON
            try:
                data = json.loads(native.data)
                public_token = data.get("public_token") or data.get("publicToken")
            except:
                pass
        if not public_token:
            raise Exception("Не удается получить public_token")

        success, tokenized_card = await tokenize_card(public_token, card)
        if not success or not tokenized_card:
            raise Exception("Не удалось токенизировать карту")

        send_data = await client(
            SendPaymentFormRequest(
                form_id=form_info.form_id,  # type: ignore
                invoice=invoice,
                credentials=InputPaymentCredentials(data=DataJSON(tokenized_card)),
            )
        )

        orm_account.busy = False
        await orm_account.save()
        if isinstance(send_data, PaymentVerificationNeeded):
            return BuyPremiumOut(status="success", verification_url=send_data.url)
        else:
            return BuyPremiumOut(status="success")

    except SessionExpiredError as e:
        await logger.error(str(e))
        return BuyPremiumOut(status="error", message=str(e))
    except Exception as e:
        await logger.error(f"ошибка: {e}")
        return BuyPremiumOut(status="error", message=str(e))
    finally:
        await client.disconnect()  # type: ignore
