"""P8-1 (F11): short-term Redis memory expires at its TTLs; cache keys match the RAG shape."""

import time

import fakeredis
import pytest

from memory.short_term import (
    CACHE_TTL_SECONDS,
    SHORT_TERM_TTL_SECONDS,
    ShortTermMemory,
    cache_key,
)
from rag.retriever import CACHE_TTL_SECONDS as RAG_TTL
from rag.retriever import cache_key as rag_cache_key


@pytest.fixture
def redis():
    return fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer(), decode_responses=True)


@pytest.fixture
def memory(redis):
    return ShortTermMemory(redis)


def test_ttls_are_24_hours_and_300_seconds_and_align_with_rag():
    assert SHORT_TERM_TTL_SECONDS == 24 * 3600
    assert CACHE_TTL_SECONDS == 300 == RAG_TTL


def test_cache_key_has_the_documented_shape_and_matches_the_retriever():
    assert cache_key("hybrid", "billing", 3, "refund seats") == "rag:hybrid:billing:3:refund seats"
    assert cache_key("keyword", None, 5, "q") == "rag:keyword::5:q"
    for args in [("hybrid", "billing", 3, "x"), ("semantic", None, 5, "y z")]:
        assert cache_key(*args) == rag_cache_key(*args)


async def test_conversation_is_ordered_and_expires_in_24_hours(memory, redis):
    await memory.append_message("T1", {"role": "customer", "text": "hi"})
    await memory.append_message("T1", {"role": "agent", "text": "hello"})
    assert [m["text"] for m in await memory.conversation("T1")] == ["hi", "hello"]
    assert await memory.conversation("T2") == []
    assert await redis.ttl("conv:T1") == SHORT_TERM_TTL_SECONDS


async def test_workflow_state_round_trips_and_expires_in_24_hours(memory, redis):
    await memory.save_workflow_state("T1", {"current_node": "risk_check", "n": 3})
    assert await memory.workflow_state("T1") == {"current_node": "risk_check", "n": 3}
    assert await memory.workflow_state("missing") is None
    assert await redis.ttl("wf:T1") == SHORT_TERM_TTL_SECONDS


async def test_each_write_refreshes_the_conversation_ttl(memory, redis):
    await memory.append_message("T1", {"text": "a"})
    await redis.expire("conv:T1", 10)
    await memory.append_message("T1", {"text": "b"})
    assert await redis.ttl("conv:T1") == SHORT_TERM_TTL_SECONDS


async def test_entries_really_expire(memory, monkeypatch):
    await memory.append_message("T1", {"text": "a"})
    await memory.save_workflow_state("T1", {"x": 1})
    await memory.cache.set("rag:hybrid::3:q", "v", CACHE_TTL_SECONDS)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + CACHE_TTL_SECONDS + 1)
    assert await memory.cache.get("rag:hybrid::3:q") is None
    assert await memory.workflow_state("T1") == {"x": 1}
    monkeypatch.setattr(time, "time", lambda: real() + SHORT_TERM_TTL_SECONDS + 1)
    assert await memory.workflow_state("T1") is None
    assert await memory.conversation("T1") == []


async def test_cache_stores_with_the_given_ttl(memory, redis):
    await memory.cache.set("rag:hybrid:billing:3:q", "v", 300)
    assert await memory.cache.get("rag:hybrid:billing:3:q") == "v"
    assert await redis.ttl("rag:hybrid:billing:3:q") == 300
    assert await memory.cache.get("nope") is None


async def test_clear_ticket_removes_both_entries(memory):
    await memory.append_message("T1", {"text": "a"})
    await memory.save_workflow_state("T1", {"x": 1})
    await memory.clear_ticket("T1")
    assert await memory.conversation("T1") == []
    assert await memory.workflow_state("T1") is None
