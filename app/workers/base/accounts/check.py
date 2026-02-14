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
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from workers.base.client import hatchet
from models import orm
from utils.account import AccountUtil
from utils.functions import pick
from utils.proxy_pool import ProxyPool
from utils.s3 import AsyncS3Client
from workers.base.accounts.exceptions import SessionExpiredError
from workers.base.accounts.stop_premium import StopPremiumIn, stop_premium
from queries.accounts import set_main_photo
from utils.logger import StreamLogger


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
    me = await app.get_me(input_peer=False)
    params = pick(
        ["id", "username", "first_name", "last_name", "premium"],
        me.to_dict(),
    )
    response = await app(GetFullUserRequest("me"))  # type: ignore
    response = cast(UserFull, response)
    params["about"] = response.full_user.about
    params["channel"] = (
        response.chats[0].username if response.chats else None  # type: ignore
    )
    orm_account.update_from_dict(params)
    # If Telegram reports premium, ensure we have a premiumed_at timestamp for UI and auditing.
    if orm_account.premium:
        orm_account.premiumed_at = orm_account.premiumed_at or tz.now()
    else:
        orm_account.premiumed_at = None  # type: ignore


class AccountsCheckIn(BaseModel):
    ids: list[int]


async def _check(orm_account: orm.Account, pool: ProxyPool, logger: StreamLogger):
    proxy = await pool.verify_proxy(orm_account)

    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    orm_account.busy = True
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy", "updated_at"])

    account = AccountUtil.from_orm(orm_account)

    client = account.create_client(proxy)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise SessionExpiredError(account.phone)

        if await is_frozen(client):
            orm_account.status = orm.AccountStatus.FROZEN
            await logger.error(f"{account.phone} заморожен")
            return

        now = datetime.now()
        prev_status = orm_account.status
        prev_muted_until = orm_account.muted_until
        prev_premium = bool(orm_account.premium)

        muted_until_now = await check_spamblock(client)

        if muted_until_now:
            # мут есть сейчас
            orm_account.status = orm.AccountStatus.MUTED
            orm_account.muted_until = muted_until_now

            if prev_status != orm.AccountStatus.MUTED:
                await logger.error(
                    f"{account.phone} в муте до {muted_until_now.strftime('%d.%m.%Y')}"
                )

        else:
            # мута нет сейчас
            if (
                prev_status == orm.AccountStatus.MUTED
                and prev_muted_until
                and prev_muted_until <= now
            ):
                orm_account.muted_until = None  # type: ignore
                orm_account.status = orm.AccountStatus.GOOD

                await logger.success(f"{account.phone} мут истёк, аккаунт в порядке")

            elif prev_status != orm.AccountStatus.MUTED:
                # аккаунт был и остаётся нормальным
                if prev_status != orm.AccountStatus.GOOD:
                    orm_account.status = orm.AccountStatus.GOOD
                    await logger.success(f"{account.phone} аккаунт в порядке")

        await renew_info(client, orm_account)
        await logger.success(f"{account.phone} данные обновлены")

        await save_photos(client, orm_account)
        await logger.success(f"{account.phone} фото скачаны")

        if orm_account.premium is False:
            orm_account.premium_stopped = False
        else:
            # Premium just appeared and recurring isn't disabled yet: schedule stop-premium.
            if (not prev_premium) and (orm_account.premium_stopped is False):
                schedule = stop_premium.schedule(
                    run_at=tz.now() + timedelta(minutes=1),
                    input=StopPremiumIn(account_id=orm_account.id),
                )
                await logger.info(f"scheduled stop-premium (premium detected): {schedule.id}")

    except SessionExpiredError:
        await logger.error(f"{account.phone} вылет из сессии")
        orm_account.status = orm.AccountStatus.EXITED

    except Exception as e:
        orm_account.status = orm.AccountStatus.BANNED
        orm_account.busy = False
        await orm_account.save()
        await logger.error(f"{account.phone} забанен {e}")
    finally:
        await client.disconnect()  # type: ignore
        orm_account.busy = False
        await orm_account.save()


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

    tasks = [_check(account, pool, logger) for account in accounts]
    await asyncio.gather(*tasks)
