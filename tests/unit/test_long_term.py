"""P8-2 (F4, F11): long-term memory keeps confident facts, skips duplicates, erases fully."""

import pytest

from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.models.entities import DEMO_TENANT_ID, Tenant
from app.repositories.customers import CustomerRepository
from app.repositories.memory import CustomerMemoryRepository
from memory.long_term import (
    CONFIDENCE_FLOOR,
    MAX_RECALL,
    MEMORY_TYPES,
    LongTermMemory,
)
from rag.embeddings import FakeEmbeddings
from rag.vector_store import InMemoryVectorStore


@pytest.fixture
async def session(tmp_path):
    engine = get_engine(f"sqlite+aiosqlite:///{tmp_path / 'lt.db'}")
    await create_tables(engine)
    async with get_sessionmaker(engine)() as s:
        s.add(Tenant(id=DEMO_TENANT_ID, name="Demo"))
        await s.commit()
        yield s
    await dispose_engine()


@pytest.fixture
async def customers(session):
    repo = CustomerRepository(session)
    a = await repo.create(name="A", email="a@x.io")
    b = await repo.create(name="B", email="b@x.io")
    await session.commit()
    return a.id, b.id


@pytest.fixture
def vectors():
    return InMemoryVectorStore()


@pytest.fixture
def memory(session, vectors):
    return LongTermMemory(CustomerMemoryRepository(session), vectors, FakeEmbeddings())


def test_the_four_types_and_the_floor():
    assert set(MEMORY_TYPES) == {"preference", "past_issue", "troubleshooting", "note"}
    assert CONFIDENCE_FLOOR == 0.7
    assert MAX_RECALL == 10


async def test_a_confident_fact_is_kept_and_recalled(memory, session, customers):
    a, _ = customers
    note = await memory.remember(a, "preference", "prefers email", confidence=0.9)
    await session.commit()
    assert note is not None and note.content == "prefers email"
    assert [n.content for n in await memory.recall(a)] == ["prefers email"]


@pytest.mark.parametrize("confidence", [0.69, 0.0])
async def test_a_fact_below_the_floor_is_discarded(memory, session, customers, confidence):
    a, _ = customers
    assert await memory.remember(a, "note", "maybe a guess", confidence=confidence) is None
    await session.commit()
    assert await memory.recall(a) == []


async def test_a_fact_exactly_at_the_floor_is_kept(memory, session, customers):
    a, _ = customers
    assert await memory.remember(a, "note", "borderline", confidence=0.7) is not None


async def test_an_exact_duplicate_is_skipped_but_another_type_is_not(memory, session, customers):
    a, _ = customers
    assert await memory.remember(a, "note", "same text") is not None
    assert await memory.remember(a, "note", "same text") is None
    assert await memory.remember(a, "preference", "same text") is not None
    await session.commit()
    assert len(await memory.recall(a)) == 2


async def test_an_unknown_type_is_rejected(memory, customers):
    with pytest.raises(ValueError, match="memory type"):
        await memory.remember(customers[0], "gossip", "x")


async def test_recall_returns_at_most_ten_newest_first(memory, session, customers):
    a, _ = customers
    for i in range(14):
        await memory.remember(a, "note", f"n{i}")
    await session.commit()
    got = [n.content for n in await memory.recall(a)]
    assert got == [f"n{i}" for i in range(13, 3, -1)]
    assert len(await memory.recall(a, limit=99)) == 10


async def test_the_scrub_hook_runs_before_dedup_and_storage(session, customers):
    a, _ = customers
    mem = LongTermMemory(
        CustomerMemoryRepository(session), scrub=lambda t: t.replace("SECRET", "X")
    )
    await mem.remember(a, "note", "has SECRET")
    assert await mem.remember(a, "note", "has SECRET") is None
    assert [n.content for n in await mem.recall(a)] == ["has X"]


async def test_notes_are_indexed_as_vectors_when_a_store_is_given(memory, vectors, customers):
    a, _ = customers
    await memory.remember(a, "note", "likes dark mode")
    assert await vectors.count() == 1


async def test_erasure_leaves_no_row_and_no_vector_and_spares_others(
    memory, session, vectors, customers
):
    a, b = customers
    for i in range(12):
        await memory.remember(a, "note", f"a{i}")
    await memory.remember(b, "note", "b0")
    await session.commit()
    assert await vectors.count() == 13

    report = await memory.erase(a)
    await session.commit()

    assert (report.rows, report.vectors) == (12, 12)
    assert await memory.recall(a) == []
    assert await CustomerMemoryRepository(session).ids_for_customer(a) == []
    assert await vectors.count() == 1
    assert [n.content for n in await memory.recall(b)] == ["b0"]
