import asyncio

from app.common.models import orm

from .model import Proxy


async def get_user_proxies(user_id: int) -> list[orm.Proxy]:
    semaphore = asyncio.Semaphore(10)

    async def check_proxy(orm_proxy: orm.Proxy) -> orm.Proxy | None:
        async with semaphore:
            proxy = Proxy.from_orm(orm_proxy)
            if await proxy.check():
                return orm_proxy
        return None

    orm_proxies = await orm.Proxy.filter(user_id=user_id).all()
    results = await asyncio.gather(*(check_proxy(p) for p in orm_proxies))
    return [p for p in results if p is not None]
