import asyncio
import httpx
import phonenumbers  # type: ignore
import re
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import cast
from uuid import uuid4

from aiopath import AsyncPath
from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import PasswordHashInvalidError, SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types.users import UserFull
from telethon.types import Message
from tortoise.exceptions import IntegrityError

from config import config
from models import orm
from queries.accounts import set_main_photo
from utils.account import AccountIn, AccountUtil
from utils.functions import clear_dir, pick
from utils.logger import StreamLogger
from utils.proxy_pool import ProxyPool
from utils.s3 import AsyncS3Client
from workers.base.accounts.utils import get_account_files
from workers.base.client import hatchet

""" 
async def _get_telegram_code(app: TelegramClient) -> str | None:
    messages = await app.get_messages(777000, limit=20)

    # Гарантируем, что messages — список
    if not isinstance(messages, list):
        messages = [messages]

    now = datetime.now(timezone.utc)

    for message in messages:
        # Проверяем нормальность сообщения
        if not isinstance(message, Message) or not message.message or not message.date:
            continue

        # Проверяем что сообщение свежее (например, не старше 2 минут)
        if (now - message.date).total_seconds() > 120:
            continue

        match = re.search(r"\b(\d{5})\b", message.message)
        if match:
            return match.group(1)

    return None


async def get_telegram_code(app: TelegramClient) -> str | None:
    for _ in range(10):
        code = await _get_telegram_code(app)
        if code:
            return code
        await asyncio.sleep(1)


async def duplicate_session(account_id: int, pool: ProxyPool, logger: StreamLogger):
    orm_account = await orm.Account.get(id=account_id)

    await logger.info("Дуплициуем сессию")

    proxy = await pool.verify_proxy(orm_account)
    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    dup_account_util = AccountUtil.from_orm(orm_account)
    dup_account_util.memory_session = True

    dup_client = dup_account_util.create_client(proxy)
    phone_code_hash = None
    code = None
    dup_session = None

    try:
        await dup_client.connect()
        result = await dup_client.send_code_request(orm_account.phone)
        phone_code_hash = result.phone_code_hash

    except Exception as e:
        await logger.error(e)
        return
    finally:
        await dup_client.disconnect()  # type: ignore

    await asyncio.sleep(2)

    main_account_util = AccountUtil.from_orm(orm_account)
    main_client = main_account_util.create_client(proxy)

    try:
        await main_client.connect()
        if not await main_client.is_user_authorized():
            await logger.error("Основной аккаунт  вылетел из сессии")
            return

        code = await get_telegram_code(main_client)
        if not code:
            await logger.error("Не удалось получить код")
            return
        await logger.success(f" Получен код: {code}")

    except Exception as e:
        await logger.error(e)
        return
    finally:
        await main_client.disconnect()  # type: ignore

    if not code or not phone_code_hash:
        return

    try:
        await dup_client.connect()
        try:
            await dup_client.sign_in(
                phone=orm_account.phone,
                code=code,
                phone_code_hash=phone_code_hash,
            )
        except SessionPasswordNeededError:
            # Если требуется 2FA пароль
            if orm_account.twofa is None:
                await logger.error("Пароль 2FA требуется, но не передан!")
                return

            try:
                await dup_client.sign_in(password=orm_account.twofa)
            except PasswordHashInvalidError:
                await logger.error("2FA пароль неверный")

        await logger.success("Сессия дуплицирована")

        dup_session = StringSession.save(dup_client.session)  # type: ignore
        try:
            await orm.Account.filter(id=orm_account.id).delete()
            await orm.AccountBackup.create(session=dup_session, id=orm_account.id)
        except:
            pass

    except Exception as e:
        await logger.error(e)
        return
    finally:
        await dup_client.disconnect()  # type: ignore
 """


class AccountsUploadIn(BaseModel):
    user_id: int
    s3path: str


class TgSessionsAccount(BaseModel):
    source_name: str
    app_id: int
    app_hash: str
    session: str
    device_model: str
    system_version: str
    app_version: str


class TgSessionsConvertError(BaseModel):
    source_name: str
    error: str


class TgSessionsConvertResponse(BaseModel):
    accounts: list[TgSessionsAccount]
    errors: list[TgSessionsConvertError]


async def unzip_from_s3(file_id: str) -> AsyncPath:
    tmp_dir = AsyncPath(tempfile.mkdtemp())

    async with AsyncS3Client() as s3:  # type: ignore
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


def _extract_phone(source_name: str) -> str | None:
    phone = re.sub(r"\D", "", source_name)
    # Avoid treating values like "acc1" as a real phone number.
    return phone if len(phone) >= 8 else None


def _resolve_country(phone: str) -> str | None:
    try:
        parsed = phonenumbers.parse(f"+{phone}")
        return phonenumbers.region_code_for_number(parsed)
    except phonenumbers.NumberParseException:
        return None


async def convert_tdata_from_s3(
    user_id: int, s3path: str, logger: StreamLogger
) -> list[AccountUtil]:
    async with AsyncS3Client() as s3:  # type: ignore
        archive_bytes = await s3.get(s3path)

    url = f"{config.tg_sessions.url.rstrip('/')}/"
    filename = s3path.rsplit("/", maxsplit=1)[-1] or "accounts.zip"
    files = {"file": (filename, archive_bytes, "application/zip")}

    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
        response = await client.post(url, files=files)
        response.raise_for_status()

    payload = TgSessionsConvertResponse.model_validate(response.json())

    for item in payload.errors:
        await logger.error(f"tdata conversion [{item.source_name}]: {item.error}")

    fallback_proxy = await (
        orm.Proxy.filter(user_id=user_id, active=True)
        .order_by("failures", "id")
        .first()
    )
    fallback_country: str | None = fallback_proxy.country if fallback_proxy else None

    converted_accounts: list[AccountUtil] = []
    for item in payload.accounts:
        phone = _extract_phone(item.source_name)

        country = _resolve_country(phone) if phone else None
        if not country:
            if not fallback_country:
                await logger.error(
                    f"tdata conversion [{item.source_name}]: could not resolve country by phone and no active proxies found for fallback"
                )
                continue
            country = fallback_country
            await logger.info(
                f"tdata conversion [{item.source_name}]: country fallback to proxy country {country}"
            )

        account_phone = phone or item.source_name[:32]

        converted_accounts.append(
            AccountUtil(
                app_id=item.app_id,
                app_hash=item.app_hash,
                device_model=item.device_model,
                system_version=item.system_version,
                app_version=item.app_version,
                twofa="",
                country=country,
                phone=account_phone,
                session_string=item.session,
            )
        )

    return converted_accounts


async def save_photos(client: TelegramClient, account_in: AccountIn):
    insert: list[orm.AccountPhoto] = []
    i = 0
    async with AsyncS3Client() as s3:  # type: ignore
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
    proxy = await pool.acquire_proxy(account.country)
    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    client = account.create_client(proxy)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await logger.error(f"{account.phone} вылетел из сессии")

            return

        me = await client.get_me(input_peer=False)
        params = pick(
            ["id", "username", "first_name", "last_name", "premium"],
            me.to_dict(),
        )
        if me.phone:
            account.phone = me.phone
            country = _resolve_country(me.phone)
            if country:
                account.country = country
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
            saved_id = orm_account.id  # <-- сохраняем, но НЕ возвращаем здесь
            await logger.success(account.phone)
        except IntegrityError:
            await logger.error(f"{account.phone} уже есть в базе")
            return None
        finally:
            # Даже если уже есть в базе — освободим прокси
            await pool.release_proxy_lock(proxy)

        try:
            await save_photos(client, account_in)
        except Exception as e:
            await logger.error(f"{account.phone} {e}")

        return saved_id
    except Exception as e:
        await logger.error(f"{account.phone} {e}")
        await pool.release_proxy_lock(proxy)

    finally:
        await client.disconnect()  # type: ignore


@hatchet.task(
    name="accounts-upload",
    input_validator=AccountsUploadIn,
    execution_timeout=timedelta(minutes=10),
    schedule_timeout=timedelta(minutes=10),
)
async def accounts_upload(input: AccountsUploadIn, ctx: Context):
    await asyncio.sleep(2)

    logger = StreamLogger(ctx)
    tmp_dir: AsyncPath | None = None

    try:
        tmp_dir = await unzip_from_s3(input.s3path)
    except zipfile.BadZipFile:
        await logger.error(
            "Не удалось распаковать файл: загруженный файл не является ZIP-архивом."
        )
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(input.s3path)
        return
    except Exception as e:
        await logger.error(f"Не удалось распаковать архив аккаунтов: {e}")
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(input.s3path)
        if tmp_dir:
            await clear_dir(tmp_dir)
        return

    try:
        files = await get_account_files(tmp_dir)
    except Exception as e:
        await logger.error(f"Не удалось прочитать файлы аккаунтов из архива: {e}")
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(input.s3path)
        await clear_dir(tmp_dir)
        return

    accounts: list[AccountUtil] = []
    if files:
        await logger.info(f"Найдено {len(files)} аккаунтов")
        for file in files:
            try:
                account = await AccountUtil.instance(file)
                accounts.append(account)
            except Exception as e:
                await logger.error(
                    f"Не удалось прочитать аккаунт из файлов {file.session.name} и {file.json.name}: {e}"
                )
    else:
        await logger.info(
            "Пары .session/.json не найдены, пробую конвертацию tdata через tg-sessions"
        )
        try:
            accounts = await convert_tdata_from_s3(input.user_id, input.s3path, logger)
        except Exception as e:
            await logger.error(f"Не удалось конвертировать tdata через tg-sessions: {e}")
            async with AsyncS3Client() as s3:  # type: ignore
                await s3.delete(input.s3path)
            await clear_dir(tmp_dir)
            return

    if not accounts:
        await logger.error("Аккаунты не найдены или не удалось подготовить к сохранению.")
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(input.s3path)
        await clear_dir(tmp_dir)
        return

    proxy_pool = ProxyPool(input.user_id)

    tasks = [
        save_account(input.user_id, account, proxy_pool, logger) for account in accounts
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    saved_ids = []
    for result in results:
        if isinstance(result, Exception):
            await logger.error(f"Ошибка при сохранении аккаунта: {result}")
            continue
        if result:
            saved_ids.append(result)

    await logger.info(f"Сохранено аккаунтов: {len(saved_ids)}")

    async with AsyncS3Client() as s3:  # type: ignore
        await s3.delete(input.s3path)
    await clear_dir(tmp_dir)

    """ tasks = [
        duplicate_session(account_id, proxy_pool, logger) for account_id in saved_ids
    ]
    await asyncio.gather(*tasks) """
