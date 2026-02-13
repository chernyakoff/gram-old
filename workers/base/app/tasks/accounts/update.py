import asyncio
from datetime import timedelta
from io import BytesIO

from hatchet_sdk import Context
from pydantic import BaseModel
from telethon import TelegramClient, types
from telethon.tl.functions.account import (
    UpdatePersonalChannelRequest,
    UpdateProfileRequest,
    UpdateUsernameRequest,
)
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import orm
from app.common.utils.account import AccountUtil
from app.common.utils.proxy_pool import ProxyPool
from app.common.utils.s3 import AsyncS3Client
from app.tasks.accounts.exceptions import SessionExpiredError
from app.utils.queries import set_main_photo
from app.utils.stream_logger import StreamLogger


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


async def update_username(
    client: TelegramClient,
    username: str,
    orm_account: orm.Account,
    logger: StreamLogger,
) -> None:
    try:
        await client(UpdateUsernameRequest(username=username))
        orm_account.username = username
        await orm_account.save()
        await logger.success("username обновлен")
    except Exception as e:
        await logger.error("ошибка обновления username")
        await logger.tech(
            "update_username failed",
            payload={"account_id": orm_account.id, "username": username},
            exc=e,
        )


async def update_profile(
    client: TelegramClient,
    update: dict[str, str],
    orm_account: orm.Account,
    logger: StreamLogger,
):
    try:
        await client(UpdateProfileRequest(**update))
        orm_account.update_from_dict(update)
        await orm_account.save()
        await logger.success("профиль обновлен")
    except Exception as e:
        await logger.error("ошибка обновления профиля")
        await logger.tech(
            "update_profile failed",
            payload={"account_id": orm_account.id, "update": update},
            exc=e,
        )


async def update_channel(
    client: TelegramClient,
    channel: str,
    orm_account: orm.Account,
    logger: StreamLogger,
):
    try:
        await client(UpdatePersonalChannelRequest(channel=channel))  # type: ignore
        orm_account.channel = channel
        await orm_account.save()
        await logger.success("канал обновлен")
    except Exception as e:
        await logger.error("ошибка обновления канала")
        await logger.tech(
            "update_channel failed",
            payload={"account_id": orm_account.id, "channel": channel},
            exc=e,
        )


async def delete_photos(
    client: TelegramClient,
    to_delete: list[int],
    account_id: int,
    logger: StreamLogger,
):
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
    except Exception as e:
        await logger.error("ошибка удаления фото")
        await logger.tech(
            "delete_photos failed",
            payload={"to_delete": to_delete, "paths": paths, "account_id": account_id},
            exc=e,
        )


async def upload_photos(
    client: TelegramClient, to_upload: list[str], account_id: int, logger: StreamLogger
):
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
            except Exception as e:
                await logger.error(f"ошибка загрузки фото: {path.split('/')[-1]}")
                await logger.tech(
                    "upload_photos failed",
                    payload={"path": path, "account_id": account_id},
                    exc=e,
                )
    await set_main_photo(account_id)


async def update(
    client: TelegramClient,
    input: AccountsUpdateIn,
    orm_account: orm.Account,
    logger: StreamLogger,
):
    fields = ["username", "about", "channel", "first_name", "last_name"]
    to_change = compare_models(orm_account, input, fields)

    if "username" in to_change:
        username = input.username or ""
        await update_username(client, username, orm_account, logger)

    profile_update = {
        f: getattr(input, f) or ""
        for f in ["about", "first_name", "last_name"]
        if f in to_change
    }
    if profile_update:
        await update_profile(client, profile_update, orm_account, logger)

    if "channel" in to_change:
        channel = input.channel or ""
        await update_channel(client, channel, orm_account, logger)

    if input.photos.delete:
        await delete_photos(client, input.photos.delete, orm_account.id, logger)

    if input.photos.upload:
        await upload_photos(client, input.photos.upload, orm_account.id, logger)


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
