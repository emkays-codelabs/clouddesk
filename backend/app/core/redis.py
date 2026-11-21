from functools import lru_cache

import fakeredis
import redis.asyncio as aioredis

from app.core.config import get_settings


@lru_cache
def get_redis() -> aioredis.Redis:
    """The shared async Redis client.

    Real Redis only when REDIS_URL is set and USE_FAKE_REDIS is off; otherwise an in-process
    fakeredis so the demo and the tests need no server. Cached per process; tests call
    `get_redis.cache_clear()` to get a fresh, empty instance.
    """
    settings = get_settings()
    if settings.use_fake_redis or not settings.redis_url:
        # An explicit server per instance, so two instances never share keys by accident.
        return fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer(), decode_responses=True)
    return aioredis.from_url(settings.redis_url, decode_responses=True)
