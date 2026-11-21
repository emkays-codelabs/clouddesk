from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.schemas.common import MessageRole, Severity, TicketStatus


async def _seed(session):
    cust = await CustomerRepository(session).create(name="Ada", email="ada@x.io")
    other = await CustomerRepository(session).create(name="Bob", email="bob@x.io")
    repo = TicketRepository(session)
    t1 = await repo.create(
        ticket_number="CD-1001", customer_id=cust.id, subject="SSO login fails", body="b",
        status=TicketStatus.new, severity=Severity.high,
    )  # fmt: skip
    t2 = await repo.create(
        ticket_number="CD-1002", customer_id=cust.id, subject="Refund please", body="seats",
        status=TicketStatus.resolved, severity=Severity.low,
    )  # fmt: skip
    t3 = await repo.create(
        ticket_number="CD-1003", customer_id=other.id, subject="API 429", body="b",
        status=TicketStatus.new, severity=Severity.low,
    )  # fmt: skip
    await session.commit()
    return repo, cust, other, t1, t2, t3


def _ids(result):
    return {t.id for t in result[0]}


async def test_get_and_get_by_number(session, tenants):
    repo, _, _, t1, t2, _ = await _seed(session)
    assert (await repo.get(t1.id)).ticket_number == "CD-1001"
    assert (await repo.get_by_number("CD-1002")).id == t2.id
    assert await repo.get_by_number("CD-9999") is None


async def test_list_filters_on_status_severity_and_search(session, tenants):
    repo, _, _, t1, t2, t3 = await _seed(session)
    assert _ids(await repo.list(status=TicketStatus.new)) == {t1.id, t3.id}
    assert _ids(await repo.list(severity=Severity.low)) == {t2.id, t3.id}
    assert _ids(await repo.list(status=TicketStatus.new, severity=Severity.low)) == {t3.id}
    assert _ids(await repo.list(search="REFUND")) == {t2.id}
    assert _ids(await repo.list(search="cd-1003")) == {t3.id}
    _, total = await repo.list(page=1, page_size=1)
    assert total == 3


async def test_list_for_customer_excludes_current_newest_first_and_honours_limit(session, tenants):
    repo, cust, _, t1, t2, _ = await _seed(session)
    t4 = await repo.create(ticket_number="CD-1004", customer_id=cust.id, subject="s", body="b")
    await session.commit()
    rows = await repo.list_for_customer(cust.id, exclude_ticket_id=t4.id)
    assert [t.id for t in rows] == [t2.id, t1.id]
    rows = await repo.list_for_customer(cust.id, exclude_ticket_id=t4.id, limit=1)
    assert [t.id for t in rows] == [t2.id]


async def test_update_leaves_untouched_fields_alone(session, tenants):
    repo, _, _, t1, *_ = await _seed(session)
    updated = await repo.update(t1.id, status=TicketStatus.in_progress)
    await session.commit()
    assert updated.status == TicketStatus.in_progress
    assert updated.severity == Severity.high and updated.subject == "SSO login fails"
    assert await repo.update("missing", status=TicketStatus.closed) is None


async def test_messages_come_back_in_insertion_order(session, tenants):
    repo, _, _, t1, *_ = await _seed(session)
    msgs = TicketMessageRepository(session)
    for i in range(4):
        await msgs.add(ticket_id=t1.id, role=MessageRole.customer, body=f"m{i}")
    await session.commit()
    assert [m.body for m in await msgs.list_for_ticket(t1.id)] == ["m0", "m1", "m2", "m3"]
