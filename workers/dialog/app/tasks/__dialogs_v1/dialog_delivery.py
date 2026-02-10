import asyncio
import random

from telethon import TelegramClient

from app.common.models import orm
from app.utils.logger import Logger

from .session_timer import SessionTimer
from .telegram_service import TelegramService


class DeliveryService:
    """Delivery layer: typing/read ack + sending replies."""

    def __init__(
        self,
        client: TelegramClient,
        telegram: TelegramService,
        logger: Logger,
        session_timer: SessionTimer,
    ):
        self.client = client
        self.telegram = telegram
        self.logger = logger
        self.session_timer = session_timer

    async def send_plain(self, recipient: orm.Recipient, text: str):
        msg = await self.telegram.send_message(recipient, text)
        if msg:
            self.session_timer.reset(5)
        return msg

    async def send_reply(self, event, recipient: orm.Recipient, text: str):
        if event:
            await asyncio.sleep(random.randint(3, 10))
            await self.client.send_read_acknowledge(event.chat_id)

            async with self.client.action(event.chat_id, "typing"):  # type: ignore
                await asyncio.sleep(random.randint(10, 20))
                msg = await self.telegram.send_message(recipient, text)
        else:
            msg = await self.telegram.send_message(recipient, text)

        if msg:
            self.session_timer.reset(5)
        return msg
