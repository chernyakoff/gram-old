import asyncio
import re
import uuid
from datetime import datetime
from io import BytesIO
from typing import cast

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.functions import pick
from app.common.utils.s3 import AsyncS3Client
from app.tasks.accounts.exceptions import SessionExpiredError
from app.tasks.accounts.model import Account
from app.tasks.proxies.pool import ProxyPool
from app.tasks.proxies.utils import get_user_proxies
from app.utils.queries import set_main_photo
from app.utils.stream_logger import StreamLogger
from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import UserDeactivatedBanError, UserDeactivatedError
from telethon.errors.rpcerrorlist import UsernameNotOccupiedError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types.users import UserFull


async def is_frozen(
    client: TelegramClient, username: str = "Telegram", timeout: float = 5.0
) -> bool:
    try:
        return await asyncio.wait_for(_check_entity(client, username), timeout=timeout)
    except asyncio.TimeoutError:
        return False


async def _check_entity(client: TelegramClient, username: str) -> bool:
    try:
        await client.get_entity(username)
        return False  # Если инфу получили — аккаунт ок
    except (UserDeactivatedError, UserDeactivatedBanError):
        return True  # Заморожен/забанен
    except UsernameNotOccupiedError:
        # Аналог "No user has X"
        return True
    except Exception as e:
        # Иногда Telegram шлёт тексты типа "FROZEN" как plain message
        if "FROZEN" in str(e).upper():
            return True
        # Любая другая ошибка — пробрасываем
        raise


async def check_spamblock(app: TelegramClient) -> datetime | None:
    await app.send_message("spambot", "/start")
    await asyncio.sleep(1)
    messages = await app.get_messages("spambot", limit=1)
    if not messages:
        return

    if isinstance(messages, list):
        text = messages[0].message
    else:
        text = messages.message
    if len(text) < 120:
        return
    forever = datetime.now().replace(year=datetime.now().year + 10)
    matches = re.search(r"\d+\s\w+\s\d+,\s\d+:\d+\s\w+", text)
    if matches:
        try:
            return datetime.strptime(matches[0], "%d %b %Y, %H:%M %Z")
        except:
            return forever
    else:
        return forever


async def delete_accounts_photos_task(paths: list[str]):
    async with AsyncS3Client() as s3:  # type: ignore
        await s3.delete_many(paths)


async def delete_accounts_photos(account_id: int):
    photos = await orm.AccountPhoto.filter(account_id=account_id).all()
    asyncio.create_task(delete_accounts_photos_task([p.path for p in photos]))
    await orm.AccountPhoto.filter(account_id=account_id).delete()


async def save_photos(client: TelegramClient, account: orm.Account):
    await delete_accounts_photos(account.id)

    insert: list[orm.AccountPhoto] = []
    i = 0

    async with AsyncS3Client() as s3:  # type: ignore
        async for photo in client.iter_profile_photos("me"):
            buf = BytesIO()
            await client.download_media(photo, file=buf)
            buf.seek(0)  # важно!
            path = f"media/{account.user_id}/{account.id}/{uuid.uuid4()}.png"
            await s3.put(path, buf.getvalue(), "image/png")
            insert.append(
                orm.AccountPhoto(
                    tg_id=photo.id,
                    path=path,
                    account_id=account.id,
                    access_hash=photo.access_hash,
                    file_reference=photo.file_reference,
                )
            )
            i += 1
    if insert:
        insert.reverse()
        await orm.AccountPhoto.bulk_create(insert, ignore_conflicts=True)
        await set_main_photo(account.id)


async def renew_info(app: TelegramClient, orm_account: orm.Account):
    response = await app(GetFullUserRequest("me"))  # type: ignore
    response = cast(UserFull, response)
    params = pick(
        ["id", "username", "first_name", "last_name", "premium"],
        response.users[0],
    )
    params["about"] = response.full_user.about
    params["channel"] = (
        response.chats[0].username if response.chats else None  # type: ignore
    )
    orm_account.update_from_dict(params)


class AccountsCheckIn(BaseModel):
    ids: list[int]


@hatchet.task(name="accounts-check", input_validator=AccountsCheckIn)
async def accounts_check(input: AccountsCheckIn, ctx: Context):
    await asyncio.sleep(2)  # эмуляция задержки
    logger = StreamLogger(ctx)
    accounts = await orm.Account.filter(id__in=input.ids).all()
    user_id = accounts[0].user_id
    proxies = await get_user_proxies(user_id)
    if not proxies:
        await logger.error("Отсутсвуют валидные прокси")
        return

    pool = ProxyPool(user_id)

    for orm_account in accounts:
        account = await Account.from_orm(orm_account)
        try:
            async with pool.proxy(account.country, timeout=30) as proxy:
                client = account.create_client(proxy)

                try:
                    await client.connect()

                    if not await client.is_user_authorized():
                        raise SessionExpiredError(account.phone)

                    if await is_frozen(client):
                        orm_account.status = enums.AccountStatus.FROZEN
                        await logger.error(f"{account.phone} заморожен")
                        continue

                    muted_until = await check_spamblock(client)
                    if muted_until:
                        orm_account.status = enums.AccountStatus.MUTED
                        orm_account.muted_until = muted_until
                        await logger.error(
                            f"{account.phone} в муте до {muted_until.strftime('%d.%m.%Y')}"
                        )
                        continue
                    else:
                        orm_account.muted_until = None  # type: ignore

                    await renew_info(client, orm_account)
                    await logger.success(f"{account.phone} данные обновлены")

                    await save_photos(client, orm_account)
                    await logger.success(f"{account.phone} фото скачаны")

                    orm_account.status = enums.AccountStatus.GOOD
                    await logger.success(f"{account.phone} в порядке!")

                except SessionExpiredError:
                    await logger.error(f"{account.phone} вылет из сессии")
                    orm_account.status = enums.AccountStatus.EXITED

                except Exception as e:
                    orm_account.status = enums.AccountStatus.BANNED
                    await orm_account.save()
                    await logger.error(f"{account.phone} забанен {e}")
                finally:
                    await client.disconnect()  # type: ignore
                    await orm_account.save()

        except TimeoutError:
            await logger.warning("нет доступного прокси")
        except Exception as e:
            await logger.error(f"неизвестная ошибка: {e}")

        await asyncio.sleep(1)
