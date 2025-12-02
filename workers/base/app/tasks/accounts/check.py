import asyncio
import re
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import cast

from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types.users import UserFull

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.account import AccountUtil
from app.common.utils.functions import pick
from app.common.utils.proxy_pool import ProxyPool
from app.common.utils.s3 import AsyncS3Client
from app.tasks.accounts.exceptions import SessionExpiredError
from app.utils.queries import set_main_photo
from app.utils.stream_logger import StreamLogger


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

    except Exception:
        return True


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


@hatchet.task(
    name="accounts-check",
    input_validator=AccountsCheckIn,
    execution_timeout=timedelta(minutes=60),
    schedule_timeout=timedelta(minutes=60),
)
async def accounts_check(input: AccountsCheckIn, ctx: Context):
    await asyncio.sleep(2)  # эмуляция задержки
    logger = StreamLogger(ctx)
    accounts = (
        await orm.Account.filter(id__in=input.ids).prefetch_related("proxy").all()
    )
    user_id = accounts[0].user_id

    pool = ProxyPool(user_id)

    for orm_account in accounts:
        proxy = await pool.ensure_account_has_working_proxy(orm_account)

        if not proxy:
            await logger.from_proxy_pool(pool)
            continue

        account = await AccountUtil.from_orm(orm_account)

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

        await asyncio.sleep(1)
