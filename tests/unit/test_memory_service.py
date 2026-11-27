"""P8-3 (F4, F11, N7): the memory service recalls, records, scrubs and stays idempotent."""

import pytest
from sqlalchemy import select

from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.core.scrub import find_secrets, scrub
from app.models.entities import DEMO_TENANT_ID, CustomerMemory, Tenant
from app.repositories.customers import CustomerRepository
from app.repositories.memory import CustomerMemoryRepository
from app.repositories.tickets import TicketRepository
from app.schemas.common import Severity, TicketStatus
from memory.long_term import LongTermMemory
from memory.memory_service import MemoryService

CARD = "4111 1111 1111 1111"
KEY = "sk-abcdefghijklmnopqrstuvwx1234"
STEPS = ["Check SSO config", "Clear the cache", "Re-issue the certificate", "Call support"]
BODY = "Hi, my SSO login fails since Monday and nobody in the team can get in at all."


@pytest.fixture
async def session(tmp_path):
    engine = get_engine(f"sqlite+aiosqlite:///{tmp_path / 'ms.db'}")
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
    tickets = TicketRepository(session)
    for i in range(5):
        await tickets.create(
            id=f"T{i}", ticket_number=f"CD-{i}", customer_id=a.id, subject="s", body="b",
            status=TicketStatus.new, severity=Severity.low,
        )  # fmt: skip
    await session.commit()
    return a.id, b.id


@pytest.fixture
def service(session):
    return MemoryService(LongTermMemory(CustomerMemoryRepository(session)), scrub)


async def _rows(session):
    return list((await session.execute(select(CustomerMemory))).scalars().all())


async def test_record_writes_past_issue_three_steps_and_a_resolution_note(
    service, session, customers
):
    a, _ = customers
    report = await service.record_resolution(
        a, "T1", "login_issue", "SSO fails", STEPS, "Re-issued the certificate"
    )
    await session.commit()
    by_type = {}
    for n in await service.recall_customer(a):
        by_type.setdefault(n.memory_type, []).append(n.content)
    assert len(report.written) == 5
    assert by_type["past_issue"] == ["login_issue: SSO fails"]
    assert sorted(by_type["troubleshooting"]) == [
        f"Step {i}: {s}" for i, s in enumerate(STEPS[:3], 1)
    ]
    assert by_type["note"] == ["Resolution: Re-issued the certificate"]
    assert all(n.source_ticket_id == "T1" for n in await service.recall_customer(a))


async def test_recording_the_same_resolution_twice_leaves_one_resolution_note(
    service, session, customers
):
    a, _ = customers
    args = (a, "T1", "billing", "Refund", STEPS, "Refunded 3 seats")
    await service.record_resolution(*args)
    again = await service.record_resolution(*args)
    await session.commit()
    notes = [r for r in await _rows(session) if r.memory_type == "note"]
    assert len(notes) == 1 and len(await _rows(session)) == 5
    assert again.written == [] and again.skipped == 5


async def test_recall_returns_at_most_ten(service, session, customers):
    a, _ = customers
    for i in range(4):
        await service.record_resolution(a, f"T{i}", "other", f"s{i}", STEPS, f"r{i}")
    await session.commit()
    assert len(await service.recall_customer(a)) == 10


async def test_cards_keys_and_passwords_never_reach_the_table(service, session, customers):
    a, _ = customers
    await service.record_resolution(
        a,
        "T1",
        "billing",
        f"Customer pasted card {CARD}",
        [f"Asked about {KEY}", "password=hunter2hunter was shared", "ok"],
        f"Closed. Card {CARD} was masked, password: Tr0ub4dor&3",
    )
    await session.commit()
    rows = await _rows(session)
    assert rows
    for row in rows:
        assert find_secrets(row.content) == [], row.content
        for leaked in ("4111", "abcdefghijklmnopqrstuv", "hunter2hunter", "Tr0ub4dor"):
            assert leaked not in row.content


async def test_a_note_containing_the_raw_ticket_body_is_dropped(service, session, customers):
    a, _ = customers
    report = await service.record_resolution(
        a, "T1", "login_issue", BODY, ["Check config"], "Fixed", ticket_body=BODY
    )
    await session.commit()
    assert report.skipped == 1
    assert all(BODY not in r.content for r in await _rows(session))
    assert len(await _rows(session)) == 2


async def test_nothing_is_stored_for_another_customer(service, session, customers):
    a, b = customers
    await service.record_resolution(a, "T1", "other", "s", STEPS, "r")
    await session.commit()
    assert await service.recall_customer(b) == []
    assert {r.customer_id for r in await _rows(session)} == {a}


async def test_low_confidence_records_nothing(service, session, customers):
    a, _ = customers
    report = await service.record_resolution(a, "T1", "other", "s", STEPS, "r", confidence=0.5)
    assert report.written == [] and await _rows(session) == []


async def test_the_app_adapter_scrubs_and_erases(session, customers):
    from app.services.customer_memory_service import build_memory_service, erase_customer_memory

    a, _ = customers
    svc = build_memory_service(session)
    await svc.record_resolution(a, "T1", "billing", f"card {CARD}", STEPS, "done")
    await session.commit()
    assert all("4111" not in r.content for r in await _rows(session))

    report = await erase_customer_memory(session, a)
    await session.commit()
    assert report.rows == 5 and await _rows(session) == []
