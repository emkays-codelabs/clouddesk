"""Adapt the shared Redis client to the cache object `rag.retriever` expects.

Does: expose `get(key)` and `set(key, value, ttl)` over an async Redis client, so `rag/` never
imports `app`. Must NOT: hold retrieval logic or know what is cached.
"""

from typing import Any

from app.core.redis import get_redis


class RedisRetrievalCache:
    def __init__(self, redis: Any | None = None) -> None:
        self._redis = redis if redis is not None else get_redis()

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self._redis.set(key, value, ex=ttl)
