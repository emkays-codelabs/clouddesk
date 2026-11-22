"""P6-3: write tools go through the registry; approval, idempotency and read-back verification."""

import pytest
import sqlalchemy as sa

from app.core.config import Settings
from app.models.entities import Escalation, ResolutionAction, Ticket
from app.repositories.customers import SubscriptionRepository, WorkspaceRepository
from app.repositories.tickets import TicketRepository
from app.repositories.workflow import WorkflowRunRepository
from app.tools.factory import WRITE_TOOL_NAMES, build_default_registry


@pytest.fixture
async def env(tool_env):
    """(ctx, ticket, workflow_id, trusted refund values, refund args) for the CD-1002 scenario."""
    async with tool_env.session_factory() as s:
        ticket = await TicketRepository(s).get_by_number("CD-1002")
        sub = await SubscriptionRepository(s).get_for_customer(ticket.customer_id)
        run = await WorkflowRunRepository(s).create(ticket_id=ticket.id, thread_id="th-1")
        await s.commit()
    trusted = {ticket.customer_id, sub.id, 24.0, ticket.id}
    refund_args = {
        "customer_id": ticket.customer_id,
        "subscription_id": sub.id,
        "amount": 24.0,
        "reason": "Charged for 8 seats, uses 5",
    }
    return tool_env, ticket, run.id, trusted, refund_args


async def _rows(ctx, model):
    async with ctx.session_factory() as s:
        return list((await s.execute(sa.select(model))).scalars().all())


def test_write_tools_are_registered_with_policy_flags(tool_env):
    listed = {t["name"]: t for t in build_default_registry(tool_env).list_tools()}
    assert set(WRITE_TOOL_NAMES) <= set(listed)
    assert listed["create_refund_request"]["requires_approval"] is True
    assert listed["reset_demo_setting"]["requires_approval"] is True
    assert listed["update_ticket"]["requires_approval"] is False
    assert listed["create_escalation"]["requires_approval"] is False
    assert all(listed[n]["description"] for n in WRITE_TOOL_NAMES)
    assert len(listed) == 9


async def test_refund_without_approval_writes_nothing(env):
    ctx, ticket, wf, trusted, args = env
    reg = build_default_registry(ctx)
    res = await reg.execute(
        "create_refund_request", args, ticket_id=ticket.id, workflow_id=wf, trusted_values=trusted
    )
    assert not res.ok and res.error == "approval_required"
    assert ctx.integrations.billing.calls == []
    assert await _rows(ctx, ResolutionAction) == []


async def test_approved_refund_is_recorded_once_and_verified(env):
    ctx, ticket, wf, trusted, args = env
    reg = build_default_registry(ctx)
    kw = {"ticket_id": ticket.id, "workflow_id": wf, "trusted_values": trusted}
    first = await reg.execute("create_refund_request", args, approved=True, **kw)
    assert first.ok and not first.idempotent
    assert first.data["amount"] == 24.0 and first.data["refund_id"].startswith("re_mock_")
    assert first.verification["verified"] is True

    second = await reg.execute("create_refund_request", args, approved=True, **kw)
    assert second.ok and second.idempotent and second.data == first.data

    assert len(ctx.integrations.billing.refunds) == 1
    assert len(ctx.integrations.billing.calls) == 1
    rows = await _rows(ctx, ResolutionAction)
    assert len(rows) == 1
    row = rows[0]
    assert row.tool == "create_refund_request" and row.status == "executed"
    assert row.requires_approval is True and row.verification["verified"] is True
    assert row.idempotency_key.startswith(f"{ticket.id}:create_refund_request:")


async def test_a_new_registry_over_the_same_database_still_refuses_a_second_refund(env):
    ctx, ticket, wf, trusted, args = env
    kw = {"ticket_id": ticket.id, "workflow_id": wf, "trusted_values": trusted}
    await build_default_registry(ctx).execute("create_refund_request", args, approved=True, **kw)
    again = await build_default_registry(ctx).execute(
        "create_refund_request", args, approved=True, **kw
    )
    assert again.ok and again.idempotent
    assert len(ctx.integrations.billing.refunds) == 1
    assert len(await _rows(ctx, ResolutionAction)) == 1


async def test_refund_amount_from_ticket_text_is_rejected_before_anything_is_written(env):
    ctx, ticket, wf, trusted, args = env
    res = await build_default_registry(ctx).execute(
        "create_refund_request",
        {**args, "amount": 9999.0},
        approved=True,
        ticket_id=ticket.id,
        workflow_id=wf,
        trusted_values=trusted,
    )
    assert not res.ok and res.error == "provenance_failed"
    assert ctx.integrations.billing.calls == [] and await _rows(ctx, ResolutionAction) == []


async def test_refund_for_a_subscription_of_another_customer_fails_and_writes_nothing(env):
    ctx, ticket, wf, trusted, args = env
    async with ctx.session_factory() as s:
        stmt = sa.select(Ticket).where(Ticket.customer_id != ticket.customer_id)
        other = (await s.execute(stmt)).scalars().first()
        other_sub = await SubscriptionRepository(s).get_for_customer(other.customer_id)
    res = await build_default_registry(ctx).execute(
        "create_refund_request",
        {**args, "subscription_id": other_sub.id},
        approved=True,
        ticket_id=ticket.id,
        workflow_id=wf,
        trusted_values=trusted | {other_sub.id},
    )
    assert not res.ok and "does not belong" in res.error
    assert ctx.integrations.billing.calls == [] and await _rows(ctx, ResolutionAction) == []


async def test_refund_threshold_applies_only_when_refund_approval_is_off(env):
    ctx, ticket, wf, trusted, args = env
    ctx.settings = Settings(approval_required_for_refunds=False, max_refund_without_approval=50)
    reg = build_default_registry(ctx)
    kw = {"ticket_id": ticket.id, "workflow_id": wf}
    ok = await reg.execute("create_refund_request", args, trusted_values=trusted, **kw)
    assert ok.ok
    big = {**args, "amount": 80.0}
    res = await reg.execute("create_refund_request", big, trusted_values=trusted | {80.0}, **kw)
    assert not res.ok and res.error == "approval_required"


async def test_write_without_a_workflow_id_is_refused_before_it_runs(env):
    ctx, ticket, _wf, trusted, args = env
    res = await build_default_registry(ctx).execute(
        "create_refund_request", args, approved=True, ticket_id=ticket.id, trusted_values=trusted
    )
    assert not res.ok and res.error == "workflow_id_required"
    assert ctx.integrations.billing.calls == []


async def test_update_ticket_needs_no_approval_and_is_read_back(env):
    ctx, ticket, wf, _t, _a = env
    res = await build_default_registry(ctx).execute(
        "update_ticket",
        {"ticket_id": ticket.id, "status": "in_progress", "assigned_to": "sam"},
        ticket_id=ticket.id,
        workflow_id=wf,
    )
    assert res.ok and res.verification["verified"] is True
    assert res.data["updated"] == {"status": "in_progress", "assigned_to": "sam"}
    async with ctx.session_factory() as s:
        row = await TicketRepository(s).get(ticket.id)
    assert row.status == "in_progress" and row.assigned_to == "sam"


async def test_update_ticket_with_an_invalid_status_fails_and_leaves_the_ticket(env):
    ctx, ticket, wf, _t, _a = env
    res = await build_default_registry(ctx).execute(
        "update_ticket",
        {"ticket_id": ticket.id, "status": "banana"},
        ticket_id=ticket.id,
        workflow_id=wf,
    )
    assert not res.ok
    async with ctx.session_factory() as s:
        assert (await TicketRepository(s).get(ticket.id)).status == ticket.status
    assert await _rows(ctx, ResolutionAction) == []


async def test_create_escalation_records_and_marks_the_ticket(env):
    ctx, ticket, wf, _t, _a = env
    res = await build_default_registry(ctx).execute(
        "create_escalation",
        {"ticket_id": ticket.id, "reason": "Payment dispute", "assigned_team": "billing-ops"},
        ticket_id=ticket.id,
        workflow_id=wf,
    )
    assert res.ok and res.verification["verified"] is True
    escalations = await _rows(ctx, Escalation)
    assert len(escalations) == 1 and escalations[0].assigned_team == "billing-ops"
    assert escalations[0].id == res.data["escalation_id"]
    async with ctx.session_factory() as s:
        row = await TicketRepository(s).get(ticket.id)
    assert row.escalation_required is True and row.status == "escalated"


async def test_create_escalation_twice_makes_one_escalation(env):
    ctx, ticket, wf, _t, _a = env
    reg = build_default_registry(ctx)
    args = {"ticket_id": ticket.id, "reason": "Security", "assigned_team": "security"}
    await reg.execute("create_escalation", args, ticket_id=ticket.id, workflow_id=wf)
    again = await reg.execute("create_escalation", args, ticket_id=ticket.id, workflow_id=wf)
    assert again.idempotent and len(await _rows(ctx, Escalation)) == 1


async def test_reset_demo_setting_needs_approval_then_is_verified(env):
    ctx, ticket, wf, _t, _a = env
    async with ctx.session_factory() as s:
        ws = await WorkspaceRepository(s).get_for_customer(ticket.customer_id)
    args = {"workspace_id": ws.id, "setting": "sso"}
    reg = build_default_registry(ctx)
    kw = {"ticket_id": ticket.id, "workflow_id": wf, "trusted_values": {ws.id}}
    denied = await reg.execute("reset_demo_setting", args, **kw)
    assert not denied.ok and denied.error == "approval_required"
    assert ctx.integrations.workspace_admin.calls == []
    done = await reg.execute("reset_demo_setting", args, approved=True, **kw)
    assert done.ok and done.verification["verified"] is True
    assert await ctx.integrations.workspace_admin.get_setting_state(ws.id, "sso") == "reset"


async def test_a_refund_that_cannot_be_read_back_is_not_reported_as_done(env):
    ctx, ticket, wf, trusted, args = env

    async def lost(_refund_id):
        return None

    ctx.integrations.billing.get_refund = lost
    res = await build_default_registry(ctx).execute(
        "create_refund_request",
        args,
        approved=True,
        ticket_id=ticket.id,
        workflow_id=wf,
        trusted_values=trusted,
    )
    assert not res.ok and res.error == "verification_failed"
    assert await _rows(ctx, ResolutionAction) == []
