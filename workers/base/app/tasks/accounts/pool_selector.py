from app.common.models import orm
from app.common.utils.mob_proxy_pool import MobProxyPool
from app.common.utils.proxy_pool import ProxyPool

PoolType = ProxyPool | MobProxyPool


async def build_pool(user_id: int) -> PoolType:
    has_mobile_proxy = await orm.MobProxy.filter(user_id=user_id, active=True).exists()
    if has_mobile_proxy:
        return MobProxyPool(user_id)
    return ProxyPool(user_id)


def is_mobile_pool(pool: PoolType) -> bool:
    return isinstance(pool, MobProxyPool)
