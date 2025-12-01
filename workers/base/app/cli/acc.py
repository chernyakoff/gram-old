import asyncio
import logging
from typing import cast

from cyclopts import App
from rich import print
from telethon import types
from tortoise.transactions import in_transaction

from app.common.models import orm
from app.common.utils.proxy import ProxyPool, get_user_proxies
from app.tasks.accounts.model import Account

logging.basicConfig(
    level=logging.WARNING,  # или DEBUG для больше боли
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


app = App(name="acc", help="dev tests etc")


@app.command
async def check(id: str):
    if id.isdigit():
        user = await orm.User.get_or_none(id=id)
    else:
        user = await orm.User.get_or_none(username=id.removeprefix("@"))
    if not user:
        logger.error("пользователь не найден")
        return

    proxies = await get_user_proxies(user.id)
    if not proxies:
        logger.error("отсутствуют валидные прокси")
        return

    orm_accounts = await orm.Account.filter(user_id=user.id, busy=False).all()
    if not orm_accounts:
        logger.error("отсутствуют свободные аккаунты")
        return

    pool = ProxyPool(user.id)
    for orm_account in orm_accounts:
        account = await Account.from_orm(orm_account)
        try:
            async with pool.proxy(account.country, timeout=30) as proxy:
                client = account.create_client(proxy)
                orm_account.busy = True
                async with in_transaction("default"):
                    await orm_account.save()

                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        raise Exception(f"{account.phone} - сессия недействительна")

                    me = await client.get_me()
                    me = cast(types.User, me)
                    if me.id:
                        print(f"{account.phone} в порядке")

                except Exception as e:
                    logger.error(f"{account.phone} - {e}")
                finally:
                    await client.disconnect()  # type: ignore
                    orm_account.busy = False
                    async with in_transaction("default"):
                        await orm_account.save()

        except TimeoutError:
            logger.warning("нет доступного прокси")
        except Exception as e:
            logger.error(f"неизвестная ошибка: {e}")

        await asyncio.sleep(2)
