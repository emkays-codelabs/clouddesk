import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketRepository
from app.repositories.workflow import (
    ResolutionActionRepository,
    WorkflowEventRepository,
    WorkflowRunRepository,
)
from app.schemas.common import ResolutionActionStatus, WorkflowEventType, WorkflowStatus


async def _seed(session):
    cust = await CustomerRepository(session).create(name="Ada", email="ada@x.io")
    ticket = await TicketRepository(session).create(
        ticket_number="CD-1", customer_id=cust.id, subject="s", body="b"
    )
    await session.commit()
    return ticket


async def test_latest_for_ticket_picks_the_newest_run(session, tenants):
    t = await _seed(session)
    runs = WorkflowRunRepository(session)
    await runs.create(ticket_id=t.id, thread_id="a")
    newest = await runs.create(ticket_id=t.id, thread_id="b")
    await session.commit()
    assert (await runs.latest_for_ticket(t.id)).id == newest.id
    assert [r.id for r in await runs.list_recent(limit=1)] == [newest.id]


async def test_state_json_round_trips_and_update_changes_only_given_fields(session, tenants):
    t = await _seed(session)
    runs = WorkflowRunRepository(session)
    run = await runs.create(ticket_id=t.id, thread_id="a", state={"k": [1, {"x": 2}]})
    run_id = run.id
    await runs.update(run_id, status=WorkflowStatus.completed)
    await session.commit()
    session.expire_all()
    got = await runs.get(run_id)
    assert got.state == {"k": [1, {"x": 2}]} and got.status == WorkflowStatus.completed


async def test_events_come_back_in_order_per_workflow(session, tenants):
    t = await _seed(session)
    runs, events = WorkflowRunRepository(session), WorkflowEventRepository(session)
    r1 = await runs.create(ticket_id=t.id, thread_id="a")
    r2 = await runs.create(ticket_id=t.id, thread_id="b")
    for i in range(3):
        await events.append(
            workflow_id=r1.id, ticket_id=t.id, event_type=WorkflowEventType.node_started,
            message=f"e{i}",
        )  # fmt: skip
    await events.append(
        workflow_id=r2.id, ticket_id=t.id, event_type=WorkflowEventType.error, message="x"
    )
    await session.commit()
    assert [e.message for e in await events.list_for_workflow(r1.id)] == ["e0", "e1", "e2"]
    assert len(await events.list_for_ticket(t.id)) == 4


async def test_idempotency_key_lookup_and_unique_constraint(session, tenants):
    t = await _seed(session)
    run = await WorkflowRunRepository(session).create(ticket_id=t.id, thread_id="a")
    actions = ResolutionActionRepository(session)
    kw = {
        "ticket_id": t.id,
        "workflow_id": run.id,
        "tool": "create_refund_request",
        "idempotency_key": "k1",
    }
    a = await actions.create(**kw)
    await session.commit()
    assert (await actions.get_by_idempotency_key("k1")).id == a.id
    assert await actions.get_by_idempotency_key("nope") is None
    done = await actions.record_result(
        a.id, ResolutionActionStatus.executed, {"ok": True}, {"verified": True}
    )
    assert done.result == {"ok": True} and done.verification == {"verified": True}
    assert done.status == ResolutionActionStatus.executed and done.executed_at is not None
    with pytest.raises(IntegrityError):
        await actions.create(**kw)


async def test_list_actions_for_ticket_in_creation_order(session, tenants):
    t = await _seed(session)
    run = await WorkflowRunRepository(session).create(ticket_id=t.id, thread_id="a")
    actions = ResolutionActionRepository(session)
    for key in ("k1", "k2"):
        await actions.create(ticket_id=t.id, workflow_id=run.id, tool="x", idempotency_key=key)
    await session.commit()
    assert [a.idempotency_key for a in await actions.list_for_ticket(t.id)] == ["k1", "k2"]
    assert await actions.list_for_ticket("other") == []
