from app.repositories.customers import CustomerRepository
from app.repositories.memory import CustomerMemoryRepository
from app.schemas.common import MemoryType


async def _seed(session):
    repo = CustomerRepository(session)
    return await repo.create(name="A", email="a@x.io"), await repo.create(name="B", email="b@x.io")


async def test_list_returns_at_most_ten_newest_first_for_that_customer(session, tenants):
    a, b = await _seed(session)
    mem = CustomerMemoryRepository(session)
    for i in range(12):
        await mem.add(customer_id=a.id, memory_type=MemoryType.note, content=f"a{i}")
    await mem.add(customer_id=b.id, memory_type=MemoryType.note, content="b0")
    await session.commit()
    rows = await mem.list_for_customer(a.id)
    assert [r.content for r in rows] == [f"a{i}" for i in range(11, 1, -1)]
    assert len(await mem.list_for_customer(a.id, limit=3)) == 3
    assert [r.content for r in await mem.list_for_customer(b.id)] == ["b0"]


async def test_exists_matches_exact_content_only(session, tenants):
    a, b = await _seed(session)
    mem = CustomerMemoryRepository(session)
    await mem.add(customer_id=a.id, memory_type=MemoryType.preference, content="likes email")
    await session.commit()
    assert await mem.exists(a.id, MemoryType.preference, "likes email")
    assert not await mem.exists(a.id, MemoryType.preference, "likes")
    assert not await mem.exists(a.id, MemoryType.note, "likes email")
    assert not await mem.exists(b.id, MemoryType.preference, "likes email")


async def test_delete_for_customer_removes_only_that_customers_rows(session, tenants):
    a, b = await _seed(session)
    mem = CustomerMemoryRepository(session)
    for c in (a, a, b):
        await mem.add(customer_id=c.id, memory_type=MemoryType.note, content="n")
    await session.commit()
    assert await mem.delete_for_customer(a.id) == 2
    await session.commit()
    assert await mem.list_for_customer(a.id) == []
    assert len(await mem.list_for_customer(b.id)) == 1
