import asyncio
from datetime import timedelta
from io import BytesIO

from hatchet_sdk import (
    ConcurrencyExpression,
    ConcurrencyLimitStrategy,
    Context,
)
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
from app.common.utils.s3 import AsyncS3Client
from app.tasks.accounts.exceptions import SessionExpiredError
from app.tasks.accounts.pool_selector import build_pool, is_mobile_pool
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
        await logger.error(f"ошибка обновления username: {e}")


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
        await logger.error(f"ошибка обновления профиля: {e}")


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
        await logger.error(f"ошибка обновления канала: {e}")


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
        await logger.error(f"ошибка удаления фото: {e}")


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
                await logger.error(f"ошибка загрузки фото: {e}")
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


async def _accounts_update_impl(input: AccountsUpdateIn, ctx: Context):
    await asyncio.sleep(2)  # эмуляция задержки

    logger = StreamLogger(ctx)

    orm_account = await orm.Account.get(id=input.id).prefetch_related("proxy")
    orm_account.busy = True

    pool = await build_pool(input.user_id)
    account = AccountUtil.from_orm(orm_account)

    proxy = await pool.verify_proxy(orm_account)
    if not proxy:
        await logger.from_proxy_pool(pool)
        return

    client = account.create_client(proxy)
    async with in_transaction() as conn:
        await orm_account.save(using_db=conn, update_fields=["busy"])

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise SessionExpiredError(account.phone)

        await update(client, input, orm_account, logger)

    except SessionExpiredError as e:
        await logger.error(str(e))
    except Exception as e:
        await logger.error(f"неизвестная ошибка обновления: {e}")
    finally:
        await client.disconnect()  # type: ignore
        orm_account.busy = False
        async with in_transaction() as conn:
            await orm_account.save(using_db=conn, update_fields=["busy"])
        if proxy and is_mobile_pool(pool):
            await pool.release_proxy_lock(proxy)


@hatchet.task(
    name="accounts-update",
    input_validator=AccountsUpdateIn,
    execution_timeout=timedelta(hours=1),
    schedule_timeout=timedelta(hours=1),
)
async def accounts_update(input: AccountsUpdateIn, ctx: Context):
    await _accounts_update_impl(input, ctx)


@hatchet.task(
    name="accounts-update-mp",
    input_validator=AccountsUpdateIn,
    execution_timeout=timedelta(hours=1),
    schedule_timeout=timedelta(hours=1),
    concurrency=ConcurrencyExpression(
        expression="input.user_id",
        max_runs=1,
        limit_strategy=ConcurrencyLimitStrategy.GROUP_ROUND_ROBIN,
    ),
)
async def accounts_update_mp(input: AccountsUpdateIn, ctx: Context):
    await _accounts_update_impl(input, ctx)
