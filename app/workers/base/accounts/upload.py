import asyncio
import os
import re
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import cast
from uuid import uuid4

from aiopath import AsyncPath
from hatchet_sdk import Context
from pydantic import BaseModel
from TGConvertor import SessionManager
from telethon import TelegramClient
from telethon.errors import PasswordHashInvalidError, SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types.users import UserFull
from telethon.types import Message
from tortoise.exceptions import IntegrityError

from models import orm
from queries.accounts import set_main_photo
from utils.account import AccountFile, AccountIn, AccountUtil
from utils.functions import clear_dir, pick
from utils.logger import StreamLogger
from utils.proxy_pool import ProxyPool
from utils.s3 import AsyncS3Client
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


def discover_account_sources(tmp_dir: AsyncPath) -> tuple[list[AccountFile], list[AsyncPath]]:
    session_files: list[AccountFile] = []
    tdata_folders: list[AsyncPath] = []
    seen_tdata: set[str] = set()

    for root, dirs, files in os.walk(str(tmp_dir)):
        root_path = Path(root)

        if "tdata" in dirs:
            tdata_path = root_path / "tdata"
            tdata_key = str(tdata_path.resolve())
            if tdata_key not in seen_tdata:
                seen_tdata.add(tdata_key)
                tdata_folders.append(AsyncPath(tdata_path))

        for filename in files:
            if not filename.endswith(".session"):
                continue

            session_path = root_path / filename
            json_path = session_path.with_suffix(".json")
            if json_path.exists():
                session_files.append(
                    AccountFile(
                        session=AsyncPath(session_path),
                        json=AsyncPath(json_path),
                    )
                )

    return session_files, tdata_folders


async def collect_accounts(tmp_dir: AsyncPath, logger: StreamLogger) -> list[AccountUtil]:
    session_files, tdata_folders = discover_account_sources(tmp_dir)

    if not session_files and not tdata_folders:
        return []

    if session_files:
        await logger.info(f"Найдено session+json аккаунтов: {len(session_files)}")
    if tdata_folders:
        await logger.info(f"Найдено tdata папок: {len(tdata_folders)}")

    accounts: list[AccountUtil] = []

    for file in session_files:
        try:
            account = await AccountUtil.instance(file)
            accounts.append(account)
        except Exception as e:
            await logger.error(
                f"Не удалось прочитать аккаунт из файлов {file.session.name} и {file.json.name}: {e}"
            )

    for tdata_dir in tdata_folders:
        source_name = tdata_dir.parent.name
        phone = "".join(re.findall(r"\d+", source_name)) or None
        try:
            manager = await SessionManager.from_tdata_folder(tdata_dir)
            session_string = manager.to_telethon_string()
            account = AccountUtil.from_telethon_string(
                session_string=session_string,
                phone=phone,
            )
            accounts.append(account)
        except Exception as e:
            await logger.error(
                f"Не удалось конвертировать tdata {tdata_dir}: {e}"
            )

    return accounts


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
        account_label = account.phone
        if not await client.is_user_authorized():
            await logger.error(f"{account_label} вылетел из сессии")

            return

        me = await client.get_me(input_peer=False)
        if me and me.phone:
            normalized_phone = "".join(ch for ch in me.phone if ch.isdigit())
            if normalized_phone:
                account.phone = normalized_phone
                account.country = AccountUtil.infer_country_from_phone(normalized_phone)
                account_label = normalized_phone

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
            saved_id = orm_account.id  # <-- сохраняем, но НЕ возвращаем здесь
            await logger.success(account_label)
        except IntegrityError:
            await logger.error(f"{account_label} уже есть в базе")
            return None
        finally:
            # Даже если уже есть в базе — освободим прокси
            await pool.release_proxy_lock(proxy)

        try:
            await save_photos(client, account_in)
        except Exception as e:
            await logger.error(f"{account_label} {e}")

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
        accounts = await collect_accounts(tmp_dir, logger)
    except Exception as e:
        await logger.error(f"Не удалось прочитать аккаунты из архива: {e}")
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(input.s3path)
        await clear_dir(tmp_dir)
        return

    if not accounts:
        await logger.error(
            "Аккаунты не найдены: загрузите пары .session+.json или папки tdata."
        )
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete(input.s3path)
        await clear_dir(tmp_dir)
        return

    await logger.info(f"Подготовлено аккаунтов к проверке: {len(accounts)}")

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
