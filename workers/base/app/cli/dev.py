import logging

from cyclopts import App

from app.common.models import orm
from app.utils.notify import notify_mailing_end

logging.basicConfig(
    level=logging.WARNING,  # или DEBUG для больше боли
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


LEASE_HOURS = 6  # сколько "занятый" аккаунт считается занятым
MAX_ACCOUNTS_PER_CYCLE = 50  # сколько аккаунтов проверяем за 1 тик
RECIPIENT_LEASE_MINUTES = 30  # время аренды recipient перед отправкой в таск


app = App(name="dev", help="dev tests etc")


@app.command
async def notify(id: str):
    if id.isdigit():
        user = await orm.User.get_or_none(id=id)
    else:
        user = await orm.User.get_or_none(username=id.removeprefix("@"))
    if not user:
        logger.error("пользователь не найден")
        return

    await notify_mailing_end(user.id, "тест", "test")
