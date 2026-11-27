"""Short-term memory on Redis (CLAUDE.md 7.5, F11): conversation, workflow state, retrieval cache.

Does: `ShortTermMemory(redis)` keeps the conversation per ticket (`conv:{ticket_id}`, a list) and
the workflow state (`wf:{ticket_id}`, JSON) for 24 hours, refreshed on every write, and exposes a
retrieval cache (`get(key)`, `set(key, value, ttl)`, 300 s by convention) that fits `rag.retriever`.
`cache_key` builds `rag:{mode}:{category}:{top_k}:{query}`, the same shape as the retriever's.
Must NOT: import `backend/app` (the client is an argument), outlive a TTL, store secrets.
"""

import json
from typing import Any

SHORT_TERM_TTL_SECONDS = 24 * 3600
CACHE_TTL_SECONDS = 300


def cache_key(mode: str, category: str | None, top_k: int, query: str) -> str:
    return f"rag:{mode}:{category or ''}:{top_k}:{query}"


class RetrievalCache:
    """The `get`/`set(ttl)` object `rag.retriever` expects, over any async Redis client."""

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> None:
        await self._redis.set(key, value, ex=ttl)


class ShortTermMemory:
    def __init__(self, redis: Any, ttl_seconds: int = SHORT_TERM_TTL_SECONDS) -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self.cache = RetrievalCache(redis)

    @staticmethod
    def _conv_key(ticket_id: str) -> str:
        return f"conv:{ticket_id}"

    @staticmethod
    def _state_key(ticket_id: str) -> str:
        return f"wf:{ticket_id}"

    async def append_message(self, ticket_id: str, message: dict[str, Any]) -> None:
        key = self._conv_key(ticket_id)
        await self._redis.rpush(key, json.dumps(message))
        await self._redis.expire(key, self._ttl)

    async def conversation(self, ticket_id: str) -> list[dict[str, Any]]:
        raw = await self._redis.lrange(self._conv_key(ticket_id), 0, -1)
        return [json.loads(item) for item in raw]

    async def save_workflow_state(self, ticket_id: str, state: dict[str, Any]) -> None:
        await self._redis.set(
            self._state_key(ticket_id), json.dumps(state, default=str), ex=self._ttl
        )

    async def workflow_state(self, ticket_id: str) -> dict[str, Any] | None:
        raw = await self._redis.get(self._state_key(ticket_id))
        return json.loads(raw) if raw else None

    async def clear_ticket(self, ticket_id: str) -> None:
        await self._redis.delete(self._conv_key(ticket_id), self._state_key(ticket_id))
