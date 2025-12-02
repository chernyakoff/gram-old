import asyncio
import tempfile
import zipfile
from io import BytesIO
from typing import cast
from uuid import uuid4

from aiopath import AsyncPath
from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types.users import UserFull
from tortoise.exceptions import IntegrityError

from app.client import hatchet
from app.common.models import orm
from app.common.utils.account import AccountFile, AccountIn, AccountUtil
from app.common.utils.functions import clear_dir, pick
from app.common.utils.proxy_pool import ProxyPool
from app.common.utils.s3 import AsyncS3Client
from app.utils.queries import set_main_photo
from app.utils.stream_logger import StreamLogger


class AccountsUploadIn(BaseModel):
    user_id: int
    s3path: str


async def unzip_from_s3(file_id: str) -> AsyncPath:
    tmp_dir = AsyncPath(tempfile.mkdtemp())

    async with AsyncS3Client() as s3:
        content_bytes = await s3.get(file_id)  # получаем bytes

    zip_bytes = BytesIO(content_bytes)
    with zipfile.ZipFile(zip_bytes) as zf:
        for member in zf.infolist():
            member_path = tmp_dir / member.filename
            if member.is_dir():
                await member_path.mkdir(parents=True, exist_ok=True)
            else:
                await member_path.parent.mkdir(parents=True, exist_ok=True)
                file_data = zf.read(member)
                await member_path.write_bytes(file_data)

    return tmp_dir


async def get_account_files(tmp_dir: AsyncPath) -> list[AccountFile]:
    files = [f async for f in tmp_dir.glob("*")]
    json_files = {f.stem: f for f in files if f.suffix == ".json"}
    session_files = {f.stem: f for f in files if f.suffix == ".session"}
    result = []
    for name in json_files:
        if name in session_files:
            result.append(
                AccountFile(session=session_files[name], json=json_files[name])
            )

    return result


async def save_photos(client: TelegramClient, account_in: AccountIn):
    insert: list[orm.AccountPhoto] = []
    i = 0
    async with AsyncS3Client() as s3:
        async for photo in client.iter_profile_photos("me"):
            buf = BytesIO()
            await client.download_media(photo, file=buf)
            buf.seek(0)  # важно!
            path = f"media/{account_in.user_id}/{account_in.id}/{uuid4()}.png"
            await s3.put(path, buf.getvalue(), "image/png")
            insert.append(
                orm.AccountPhoto(
                    tg_id=photo.id,
                    path=path,
                    account_id=account_in.id,
                    access_hash=photo.access_hash,
                    file_reference=photo.file_reference,
                )
            )
            i += 1
    if insert:
        insert.reverse()
        await orm.AccountPhoto.bulk_create(insert, ignore_conflicts=True)
        await set_main_photo(account_in.id)


async def save_account(
    user_id: int, account: AccountUtil, pool: ProxyPool, logger: StreamLogger
):
    proxy = await pool.acquire_for_account_loading(account)
    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    client = account.create_client(proxy)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await logger.error(f"{account.phone} вылетел из сессии")
            await pool.release_proxy_lock(proxy)
            return

        me = await client.get_me(input_peer=False)
        params = pick(
            ["id", "username", "first_name", "last_name", "premium"],
            me.to_dict(),
        )
        response = await client(GetFullUserRequest("me"))  # type: ignore
        response = cast(UserFull, response)
        params["about"] = response.full_user.about
        params["channel"] = (
            response.chats[0].username if response.chats else None  # type: ignore
        )
        params["user_id"] = user_id
        params["proxy_id"] = proxy.id
        params["session"] = StringSession.save(client.session)  # type: ignore
        account_in = AccountIn(**params)

        orm_account = account.to_orm(account_in)

        try:
            await orm_account.save()
            await logger.success(account.phone)
            await pool.release_proxy_lock(proxy)
        except IntegrityError:
            await logger.error(f"{account.phone} уже есть в базе")
            await pool.release_proxy_lock(proxy)

        try:
            await save_photos(client, account_in)
        except Exception as e:
            await logger.error(f"{account.phone} {e}")

    except Exception as e:
        await logger.error(f"{account.phone} {e}")
        await pool.release_proxy_lock(proxy)

    finally:
        await client.disconnect()  # type: ignore


@hatchet.task(name="accounts-upload", input_validator=AccountsUploadIn)
async def accounts_upload(input: AccountsUploadIn, ctx: Context):
    await asyncio.sleep(2)

    logger = StreamLogger(ctx)

    try:
        tmp_dir = await unzip_from_s3(input.s3path)

        files = await get_account_files(tmp_dir)
        if not files:
            raise ValueError("Аккаунтов не найдено")

    except Exception as e:
        await logger.error(str(e))
        async with AsyncS3Client() as s3:
            await s3.delete(input.s3path)
        if tmp_dir:
            await clear_dir(tmp_dir)

        return

    await logger.info(f"Найдено {len(files)} аккаунтов")

    accounts = []
    for file in files:
        try:
            account = await AccountUtil.instance(file)
            accounts.append(account)
        except Exception as e:
            await logger.error(e)

    proxy_pool = ProxyPool(input.user_id)

    tasks = [
        save_account(input.user_id, account, proxy_pool, logger) for account in accounts
    ]
    await asyncio.gather(*tasks)

    async with AsyncS3Client() as s3:  # type: ignore
        await s3.delete(input.s3path)
    await clear_dir(tmp_dir)
