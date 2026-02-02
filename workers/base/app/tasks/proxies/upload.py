import asyncio

from hatchet_sdk import Context
from pydantic import BaseModel
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models.enums import AccountStatus
from app.common.models.orm import Account
from app.common.utils.proxy import ProxyUtil
from app.utils.stream_logger import StreamLogger


class ProxiesUploadIn(BaseModel):
    user_id: int
    proxies: list[str]


@hatchet.task(name="proxies-upload", input_validator=ProxiesUploadIn)
async def proxies_upload(input: ProxiesUploadIn, ctx: Context):
    semaphore = asyncio.Semaphore(10)
    logger = StreamLogger(ctx)

    await logger.info(f"Найдено {len(input.proxies)} прокси")

    async def save_proxy(line: str) -> tuple[int, str] | None:
        try:
            proxy = ProxyUtil.from_line(line)

            ip = await proxy.check()
            if not ip:
                await logger.error(f"{line} Ошибка подключения")
                raise ValueError("")

            country = await proxy.get_country(ip)
            if not country:
                await logger.error(f"{line} Не определяется страна")
                raise ValueError("Не определяется страна")

            orm_proxy = proxy.to_orm(
                user_id=input.user_id,
                country=country,
            )

            await orm_proxy.save()
            await logger.success(f"{line} [{country}]")

            return orm_proxy.id, country

        except IntegrityError:
            await logger.error(f"{line} уже был загружен")
            return None

        except Exception as e:
            await logger.error(f"{line} {e}")
            return None

    async def wrapper(line: str) -> tuple[int, str] | None:
        async with semaphore:
            return await save_proxy(line)

    # ---------- ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА ----------
    results = await asyncio.gather(*(wrapper(p) for p in input.proxies))

    saved = [r for r in results if r is not None]

    await logger.info(f"Успешно загружено {len(saved)} прокси")

    if not saved:
        return

    # ---------- ГРУППИРОВКА ПО СТРАНАМ ----------
    proxies_by_country: dict[str, list[int]] = {}
    for proxy_id, country in saved:
        proxies_by_country.setdefault(country, []).append(proxy_id)

    # ---------- ПРИВЯЗКА АККАУНТОВ ----------
    async with in_transaction() as conn:
        for country, proxy_ids in proxies_by_country.items():
            accounts = await (
                Account.filter(
                    user_id=input.user_id,
                    status=AccountStatus.NOPROXY,
                    proxy_id__isnull=True,
                    country=country,
                )
                .using_db(conn)
                .limit(len(proxy_ids))
                .select_for_update()
            )

            for account, proxy_id in zip(accounts, proxy_ids):
                account.proxy_id = proxy_id
                account.status = AccountStatus.GOOD
                account.active = True

            if accounts:
                await Account.bulk_update(
                    accounts,
                    fields=("proxy_id", "status", "active"),
                    using_db=conn,
                )

            await logger.info(
                f"[{country}] привязано аккаунтов: {len(accounts)} / {len(proxy_ids)}"
            )
