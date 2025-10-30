import asyncio
from io import BytesIO
from typing import cast

from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient, types
from telethon.tl.types import DataJSON, InputInvoiceMessage, InputPaymentCredentials
from telethon.tl.types.payments import PaymentVerificationNeeded

from app.client import hatchet
from app.common.models import orm
from app.common.utils.s3 import AsyncS3Client
from app.tasks.accounts.exceptions import SessionExpiredError
from app.tasks.accounts.model import Account
from app.tasks.proxies.pool import ProxyPool
from app.tasks.proxies.utils import get_user_proxies
from app.utils.queries import set_main_photo
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


@hatchet.task(name="buy-premium", input_validator=BuyPremiumIn)
async def accounts_update(input: BuyPremiumIn, ctx: Context):
    print(input.model_dump())

    await asyncio.sleep(2)  # эмуляция задержки

    logger = StreamLogger(ctx)

    orm_account = await orm.Account.get(id=input.account_id)

    user_id = orm_account.user_id

    proxies = await get_user_proxies(user_id)
    if not proxies:
        await logger.error("отсутствуют валидные прокси")
        return

    pool = ProxyPool(user_id)
    account = await Account.from_orm(orm_account)

    try:
        async with pool.proxy(account.country, timeout=30) as proxy:
            client = account.create_client(proxy)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    raise SessionExpiredError(account.phone)

                me = await client.get_me()
                me = cast(types.User, me)
                if me.premium:
                    raise Exception("На этом аккаунте уже есть премиум")

                await client.send_message(PREMIUM_BOT, "/start")
                await asyncio.sleep(2)
                messages = await client.get_messages(
                    PREMIUM_BOT, limit=4
                )  #  messages: TotalList | Message | None
                if not messages:
                    raise Exception("PremiumBot не ответил на /start")
                if isinstance(messages, types.Message):
                    messages = [messages]

                invoice_msg = next(
                    (x for x in messages if x.invoice), None
                )  # Cannot access attribute "invoice" for class "Message"

                if not invoice_msg:
                    raise Exception("PremiumBot не дает ссылку на оплату")

                """ invoice = InputInvoiceMessage(
                    peer=invoice_msg.input_chat, msg_id=invoice_msg.id
                ) """

            except SessionExpiredError as e:
                await logger.error(str(e))
            except Exception as e:
                await logger.error(f"ошибка: {e}")
            finally:
                await client.disconnect()  # type: ignore

    except TimeoutError:
        await logger.warning("нет доступного прокси")
    except Exception as e:
        await logger.error(f"неизвестная ошибка: {e}")
