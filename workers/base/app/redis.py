import logging
import os

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def init_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_redis_url(), decode_responses=True)
        await _redis.ping()
        logger.info("Redis connected")
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis is not initialized")
    return _redis


async def shutdown_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis disconnected")
