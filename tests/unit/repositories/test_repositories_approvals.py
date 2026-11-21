from datetime import UTC, datetime, timedelta

from app.repositories.approvals import ApprovalRepository, EscalationRepository
from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketRepository
from app.repositories.workflow import WorkflowRunRepository
from app.schemas.common import ApprovalStatus, EscalationStatus


async def _seed(session):
    cust = await CustomerRepository(session).create(name="Ada", email="ada@x.io")
    t = await TicketRepository(session).create(
        ticket_number="CD-1", customer_id=cust.id, subject="s", body="b"
    )
    run = await WorkflowRunRepository(session).create(ticket_id=t.id, thread_id="a")
    await session.commit()
    return t, run


async def test_decide_changes_a_pending_row_once(session, tenants):
    t, run = await _seed(session)
    repo = ApprovalRepository(session)
    a = await repo.create(ticket_id=t.id, workflow_id=run.id, action={"tool": "refund"})
    decided = await repo.decide(a.id, ApprovalStatus.approved, "sam", "ok")
    assert decided.status == ApprovalStatus.approved and decided.decided_by == "sam"
    assert decided.decided_at is not None
    assert await repo.decide(a.id, ApprovalStatus.rejected, "vic", "late") is None
    await session.commit()
    assert (await repo.get(a.id)).status == ApprovalStatus.approved


async def test_list_filters_on_status(session, tenants):
    t, run = await _seed(session)
    repo = ApprovalRepository(session)
    a = await repo.create(ticket_id=t.id, workflow_id=run.id)
    b = await repo.create(ticket_id=t.id, workflow_id=run.id)
    await repo.decide(b.id, ApprovalStatus.rejected, "sam", None)
    await session.commit()
    assert [x.id for x in await repo.list(status=ApprovalStatus.pending)] == [a.id]
    assert len(await repo.list()) == 2


async def test_list_expired_returns_only_pending_rows_past_expiry(session, tenants):
    t, run = await _seed(session)
    repo = ApprovalRepository(session)
    now = datetime.now(UTC)
    past, future = now - timedelta(minutes=5), now + timedelta(minutes=5)
    old = await repo.create(ticket_id=t.id, workflow_id=run.id, expires_at=past)
    await repo.create(ticket_id=t.id, workflow_id=run.id, expires_at=future)
    await repo.create(ticket_id=t.id, workflow_id=run.id)
    done = await repo.create(ticket_id=t.id, workflow_id=run.id, expires_at=past)
    await repo.decide(done.id, ApprovalStatus.approved, "sam", None)
    await session.commit()
    assert [a.id for a in await repo.list_expired(now)] == [old.id]


async def test_escalation_round_trip(session, tenants):
    t, _ = await _seed(session)
    repo = EscalationRepository(session)
    e = await repo.create(ticket_id=t.id, reason="breach", assigned_team="security")
    updated = await repo.update_status(e.id, EscalationStatus.acknowledged)
    await session.commit()
    assert updated.status == EscalationStatus.acknowledged
    assert [x.id for x in await repo.list(status=EscalationStatus.acknowledged)] == [e.id]
    assert await repo.list(status=EscalationStatus.open) == []
    assert (await repo.get(e.id)).reason == "breach"
