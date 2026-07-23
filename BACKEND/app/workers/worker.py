"""
Helper for routes to enqueue background jobs without each route needing
to manage its own Redis connection lifecycle.
"""
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from app.core.config import settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool
