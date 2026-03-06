import asyncio
import random
from datetime import timedelta
from io import BytesIO

from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient, types
from telethon.errors import (
    FloodWaitError,
    RPCError,
    UsernameInvalidError,
    UsernameNotModifiedError,
    UsernameOccupiedError,
)
from telethon.tl.functions.account import (
    UpdatePersonalChannelRequest,
    UpdateProfileRequest,
    UpdateUsernameRequest,
)
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest
from tortoise.transactions import in_transaction

from models import orm
from queries.accounts import set_main_photo
from utils.account import AccountUtil
from utils.logger import StreamLogger
from utils.proxy_pool import ProxyPool
from utils.s3 import AsyncS3Client
from workers.base.accounts.exceptions import SessionExpiredError
from workers.base.client import hatchet


class AccountsUpdateStepFailedError(Exception):
    def __init__(self, failed_steps: list[str]):
        self.failed_steps = failed_steps
        super().__init__(f"Accounts update failed steps: {', '.join(failed_steps)}")


class AccountsUpdatePhotosIn(BaseModel):
    delete: list[int]
    upload: list[str]


class AccountsUpdateIn(BaseModel):
    id: int
    user_id: int
    username: str | None
    about: str | None
    channel: str | None
    first_name: str | None
    last_name: str | None
    photos: AccountsUpdatePhotosIn


def compare_models(
    orm_account: orm.Account, input: AccountsUpdateIn, fields: list[str]
) -> list[str]:
    to_change = []
    for field in fields:
        orm_val = getattr(orm_account, field, None)
        pyd_val = getattr(input, field, None)
        if orm_val != pyd_val:
            to_change.append(field)
    return to_change


def normalize_username(username: str | None) -> str:
    """
    Telegram expects username without leading '@'. Empty string means "clear username".
    """

    if not username:
        return ""
    u = username.strip()
    if u.startswith("@"):
        u = u[1:]
    return u


def _build_username_candidate(base: str, suffix: str = "") -> str:
    """
    Telegram username max length is 32.
    If suffix is present, truncate base to keep final candidate within limit.
    """

    if not base:
        return ""
    max_base_len = 32 - len(suffix)
    if max_base_len <= 0:
        return ""
    trimmed = base[:max_base_len]
    return f"{trimmed}{suffix}"


def _username_candidates(base_username: str) -> list[str]:
    """
    Candidate order:
    1) original
    2) +_YY (years 71..99 and 00..07, randomized)
    3) +YY (years 71..99 and 00..07, randomized)
    4) +3 digits (random)
    5) +4 digits (random)
    """

    base = normalize_username(base_username)
    if not base:
        return [""]

    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str):
        if candidate and candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)

    add(_build_username_candidate(base))

    years = [f"{n:02d}" for n in range(71, 100)] + [f"{n:02d}" for n in range(0, 8)]
    random.shuffle(years)
    for suffix in years:
        add(_build_username_candidate(base, f"_{suffix}"))

    random.shuffle(years)
    for suffix in years:
        add(_build_username_candidate(base, suffix))

    three_digits = random.sample(range(100, 1000), 100)
    for n in three_digits:
        add(_build_username_candidate(base, f"{n:03d}"))

    four_digits = random.sample(range(1000, 10000), 100)
    for n in four_digits:
        add(_build_username_candidate(base, f"{n:04d}"))

    return candidates


async def update_username(
    client: TelegramClient,
    username: str,
    orm_account: orm.Account,
    logger: StreamLogger,
) -> bool:
    base_username = normalize_username(username)
    candidates = _username_candidates(base_username)
    if not candidates:
        await logger.error("username пустой")
        return False

    for candidate in candidates:
        try:
            await client(UpdateUsernameRequest(username=candidate))
            orm_account.username = candidate or None  # type: ignore
            await orm_account.save()
            await logger.success("username обновлен")
            if candidate != base_username:
                await logger.info(
                    "username скорректирован из-за занятости",
                    payload={
                        "account_id": orm_account.id,
                        "requested": base_username,
                        "applied": candidate,
                    },
                )
            return True
        except UsernameOccupiedError as e:
            await logger.tech(
                "update_username occupied",
                payload={"account_id": orm_account.id, "username": candidate},
                exc=e,
            )
            continue
        except UsernameInvalidError as e:
            await logger.tech(
                "update_username invalid",
                payload={"account_id": orm_account.id, "username": candidate},
                exc=e,
            )
            continue
        except UsernameNotModifiedError as e:
            orm_account.username = candidate or None  # type: ignore
            await orm_account.save()
            await logger.info("username уже установлен")
            await logger.tech(
                "update_username not modified",
                payload={"account_id": orm_account.id, "username": candidate},
                exc=e,
            )
            return True
        except FloodWaitError as e:
            await logger.error(f"слишком часто меняли username, подождите {e.seconds} сек")
            await logger.tech(
                "update_username flood wait",
                payload={
                    "account_id": orm_account.id,
                    "username": candidate,
                    "seconds": e.seconds,
                },
                exc=e,
            )
            return False
        except RPCError as e:
            await logger.error("ошибка Telegram при обновлении username")
            await logger.tech(
                "update_username rpc error",
                payload={"account_id": orm_account.id, "username": candidate},
                exc=e,
            )
            return False
        except Exception as e:
            await logger.error("ошибка обновления username")
            await logger.tech(
                "update_username failed",
                payload={"account_id": orm_account.id, "username": candidate},
                exc=e,
            )
            return False

    await logger.error("не удалось подобрать свободный username")
    return False


async def update_profile(
    client: TelegramClient,
    update: dict[str, str],
    orm_account: orm.Account,
    logger: StreamLogger,
) -> bool:
    try:
        await client(UpdateProfileRequest(**update))
        orm_account.update_from_dict(update)
        await orm_account.save()
        await logger.success("профиль обновлен")
        return True
    except Exception as e:
        await logger.error("ошибка обновления профиля")
        await logger.tech(
            "update_profile failed",
            payload={"account_id": orm_account.id, "update": update},
            exc=e,
        )
        return False


async def update_channel(
    client: TelegramClient,
    channel: str,
    orm_account: orm.Account,
    logger: StreamLogger,
) -> bool:
    try:
        await client(UpdatePersonalChannelRequest(channel=channel))  # type: ignore
        orm_account.channel = channel
        await orm_account.save()
        await logger.success("канал обновлен")
        return True
    except Exception as e:
        await logger.error("ошибка обновления канала")
        await logger.tech(
            "update_channel failed",
            payload={"account_id": orm_account.id, "channel": channel},
            exc=e,
        )
        return False


async def delete_photos(
    client: TelegramClient,
    to_delete: list[int],
    account_id: int,
    logger: StreamLogger,
) -> bool:
    orm_photos = await orm.AccountPhoto.filter(id__in=to_delete).all()
    paths = [p.path for p in orm_photos]
    try:
        await client(
            DeletePhotosRequest(
                id=[
                    types.InputPhoto(
                        id=p.tg_id,
                        access_hash=p.access_hash,
                        file_reference=p.file_reference,
                    )
                    for p in orm_photos
                ]
            )
        )  # type: ignore

        await orm.AccountPhoto.filter(id__in=to_delete).delete()
        await logger.success("фото удалены")
        async with AsyncS3Client() as s3:  # type: ignore
            await s3.delete_many(paths)
        await set_main_photo(account_id)
        return True
    except Exception as e:
        await logger.error("ошибка удаления фото")
        await logger.tech(
            "delete_photos failed",
            payload={"to_delete": to_delete, "paths": paths, "account_id": account_id},
            exc=e,
        )
        return False


async def upload_photos(
    client: TelegramClient, to_upload: list[str], account_id: int, logger: StreamLogger
) -> bool:
    had_error = False
    async with AsyncS3Client() as s3:  # type:ignore
        for path in to_upload:
            try:
                data = await s3.get(path)
                uploaded = await client.upload_file(
                    file=BytesIO(data),
                    file_name=path.split("/")[-1],
                )
                result = await client(UploadProfilePhotoRequest(file=uploaded))
                if hasattr(result, "photo"):
                    photo: types.Photo = result.photo  # type:ignore
                    account_photo = orm.AccountPhoto(
                        account_id=account_id,
                        tg_id=photo.id,
                        path=path,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                    )
                    await account_photo.save()

                else:
                    await logger.error(
                        f"не удалось получить фото для {path}, результат: {type(result)}"
                    )
                    had_error = True
            except Exception as e:
                await logger.error(f"ошибка загрузки фото: {path.split('/')[-1]}")
                await logger.tech(
                    "upload_photos failed",
                    payload={"path": path, "account_id": account_id},
                    exc=e,
                )
                had_error = True
    await set_main_photo(account_id)
    return not had_error


async def update(
    client: TelegramClient,
    input: AccountsUpdateIn,
    orm_account: orm.Account,
    logger: StreamLogger,
):
    fields = ["username", "about", "channel", "first_name", "last_name"]
    to_change = compare_models(orm_account, input, fields)
    await logger.info(
        "поля для обновления",
        payload={"account_id": orm_account.id, "to_change": to_change},
    )
    failed_steps: list[str] = []

    if "username" in to_change:
        desired = normalize_username(input.username)
        current = normalize_username(orm_account.username)
        if desired == current:
            await logger.info("username без изменений")
        else:
            ok = await update_username(client, desired, orm_account, logger)
            if not ok:
                failed_steps.append("username")

    profile_update = {
        f: getattr(input, f) or ""
        for f in ["about", "first_name", "last_name"]
        if f in to_change
    }
    if profile_update:
        ok = await update_profile(client, profile_update, orm_account, logger)
        if not ok:
            failed_steps.append("profile")

    if "channel" in to_change:
        channel = input.channel or ""
        ok = await update_channel(client, channel, orm_account, logger)
        if not ok:
            failed_steps.append("channel")

    if input.photos.delete:
        ok = await delete_photos(client, input.photos.delete, orm_account.id, logger)
        if not ok:
            failed_steps.append("delete_photos")

    if input.photos.upload:
        ok = await upload_photos(client, input.photos.upload, orm_account.id, logger)
        if not ok:
            failed_steps.append("upload_photos")

    if failed_steps:
        await logger.error(
            "обновление аккаунта завершено частично",
            payload={"account_id": orm_account.id, "failed_steps": failed_steps},
        )
        raise AccountsUpdateStepFailedError(failed_steps)


@hatchet.task(
    name="accounts-update",
    input_validator=AccountsUpdateIn,
    execution_timeout=timedelta(minutes=10),
    schedule_timeout=timedelta(minutes=10),
)
async def accounts_update(input: AccountsUpdateIn, ctx: Context):
    await asyncio.sleep(2)  # эмуляция задержки

    logger = StreamLogger(ctx)
    client: TelegramClient | None = None
    orm_account: orm.Account | None = None
    stage = "init"
    try:
        stage = "start"
        await logger.info(
            "начинаем обновление аккаунта", payload={"account_id": input.id}
        )

        stage = "load_account"
        orm_account = await orm.Account.get(id=input.id).prefetch_related("proxy")
        orm_account.busy = True

        pool = ProxyPool(input.user_id)
        account = AccountUtil.from_orm(orm_account)

        stage = "verify_proxy"
        await logger.info("проверяем прокси")
        proxy = await pool.verify_proxy(orm_account)
        if not proxy:
            await logger.from_proxy_pool(pool)
            await logger.error("прокси не прошел проверку, обновление остановлено")
            return

        stage = "create_client"
        client = account.create_client(proxy)
        async with in_transaction() as conn:
            await orm_account.save(using_db=conn, update_fields=["busy", "updated_at"])

        stage = "connect"
        await logger.info("подключаем клиент telegram")
        await client.connect()

        stage = "auth_check"
        await logger.info("проверяем авторизацию аккаунта")
        if not await client.is_user_authorized():
            raise SessionExpiredError(account.phone)

        stage = "update_fields"
        await logger.info("запускаем обновление полей аккаунта")
        await update(client, input, orm_account, logger)
        await logger.success("обновление аккаунта завершено")

    except AccountsUpdateStepFailedError as e:
        await logger.error(
            "не удалось обновить все поля аккаунта",
            payload={
                "account_id": input.id,
                "user_id": input.user_id,
                "stage": stage,
                "failed_steps": e.failed_steps,
            },
        )
        await logger.tech(
            "accounts_update partial failure",
            payload={
                "account_id": input.id,
                "user_id": input.user_id,
                "stage": stage,
                "failed_steps": e.failed_steps,
            },
            exc=e,
        )
        raise
    except SessionExpiredError as e:
        await logger.error(
            str(e),
            payload={"account_id": input.id, "user_id": input.user_id, "stage": stage},
        )
        await logger.tech(
            "accounts_update session expired",
            payload={"account_id": input.id, "user_id": input.user_id, "stage": stage},
            exc=e,
        )
    except asyncio.CancelledError as e:
        # Cancellation (timeouts, orchestrator stop) is not an Exception in modern Python.
        # If we don't log it explicitly, the run looks like a "silent failed".
        await logger.error(
            "обновление аккаунта было отменено (timeout/stop)",
            payload={
                "account_id": input.id,
                "user_id": input.user_id,
                "stage": stage,
                "exception": type(e).__name__,
                "exception_message": str(e),
            },
        )
        await logger.tech(
            "accounts_update cancelled",
            payload={"account_id": input.id, "user_id": input.user_id, "stage": stage},
            exc=e,
        )
        raise
    except Exception as e:
        await logger.error(
            "обновление аккаунта завершилось с ошибкой. "
            "Проверьте прокси, сессию и корректность данных.",
            payload={
                "account_id": input.id,
                "user_id": input.user_id,
                "stage": stage,
                "exception": type(e).__name__,
                "exception_message": str(e),
            },
        )
        await logger.tech(
            "accounts_update failed",
            payload={"account_id": input.id, "user_id": input.user_id, "stage": stage},
            exc=e,
        )
        raise
    except BaseException as e:
        # Last-resort: ensure we log something even for non-Exception failures.
        await logger.error(
            "обновление аккаунта завершилось критической ошибкой",
            payload={
                "account_id": input.id,
                "user_id": input.user_id,
                "stage": stage,
                "exception": type(e).__name__,
                "exception_message": str(e),
            },
        )
        await logger.tech(
            "accounts_update baseexception",
            payload={"account_id": input.id, "user_id": input.user_id, "stage": stage},
            exc=e,
        )
        raise
    finally:
        if client:
            try:
                if client.is_connected():
                    await client.disconnect()  # type: ignore
            except Exception as e:
                await logger.tech(
                    "disconnect failed",
                    payload={
                        "account_id": input.id,
                        "user_id": input.user_id,
                        "stage": stage,
                    },
                    exc=e,
                )
        if orm_account:
            # Cleanup must be best-effort: if we fail to persist `busy=False` (DB issue, closed conn),
            # don't mask the real task outcome by raising from finally.
            try:
                orm_account.busy = False
                async with in_transaction() as conn:
                    await orm_account.save(
                        using_db=conn, update_fields=["busy", "updated_at"]
                    )
            except Exception as e:
                await logger.warning(
                    "не удалось сохранить статус busy=false при завершении задачи",
                    payload={
                        "account_id": input.id,
                        "user_id": input.user_id,
                        "stage": stage,
                    },
                )
                await logger.tech(
                    "accounts_update cleanup failed",
                    payload={
                        "account_id": input.id,
                        "user_id": input.user_id,
                        "stage": stage,
                    },
                    exc=e,
                )
