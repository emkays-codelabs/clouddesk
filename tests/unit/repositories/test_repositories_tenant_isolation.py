"""D1: the repository filter is the tenant boundary on SQLite, so prove it for every method."""

import importlib
import inspect
import pkgutil
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import app.repositories as repos_pkg
from app.models.entities import DEMO_TENANT_ID
from app.repositories import (
    approvals,
    audit,
    customers,
    memory,
    profiles,
    reference,
    tickets,
    workflow,
)
from app.repositories.base import ScopedRepository
from app.repositories.tenants import TenantRepository
from app.schemas.common import (
    ApprovalStatus,
    Category,
    EscalationStatus,
    MemoryType,
    MessageRole,
    ResolutionActionStatus,
    TicketStatus,
    WorkflowEventType,
)
from tests.unit.repositories.conftest import OTHER_TENANT_ID

NOW = datetime.now(UTC)


async def seed_world(session, tenant_id):
    """One row of every entity, with the same natural keys in every tenant."""

    def r(cls):
        return cls(session, tenant_id)

    cust = await r(customers.CustomerRepository).create(name="Ada", email="ada@x.io")
    await r(customers.SubscriptionRepository).create(customer_id=cust.id, plan="pro")
    await r(customers.WorkspaceRepository).create(customer_id=cust.id, name="HQ")
    profile = await r(profiles.ProfileRepository).create(email="sam@x.io", full_name="Sam")
    ticket = await r(tickets.TicketRepository).create(
        ticket_number="CD-1", customer_id=cust.id, subject="s", body="b"
    )
    await r(tickets.TicketMessageRepository).add(
        ticket_id=ticket.id, role=MessageRole.customer, body="hi"
    )
    await r(reference.IncidentRepository).create(title="outage", status="investigating")
    await r(reference.ProductRepository).create(slug="storage", name="Storage")
    article = await r(reference.SupportArticleRepository).upsert_by_slug(
        "sso", title="SSO", category=Category.login_issue, content="c"
    )
    run = await r(workflow.WorkflowRunRepository).create(ticket_id=ticket.id, thread_id="t")
    await r(workflow.WorkflowEventRepository).append(
        workflow_id=run.id, ticket_id=ticket.id, event_type=WorkflowEventType.node_started
    )
    action = await r(workflow.ResolutionActionRepository).create(
        ticket_id=ticket.id, workflow_id=run.id, tool="t", idempotency_key="k1"
    )
    approval = await r(approvals.ApprovalRepository).create(
        ticket_id=ticket.id, workflow_id=run.id, expires_at=NOW - timedelta(minutes=5)
    )
    esc = await r(approvals.EscalationRepository).create(ticket_id=ticket.id, reason="r")
    await r(memory.CustomerMemoryRepository).add(
        customer_id=cust.id, memory_type=MemoryType.note, content="n"
    )
    await r(audit.AuditLogRepository).append(actor="sam", action="POST /x")
    return SimpleNamespace(
        customer=cust.id, profile=profile.id, ticket=ticket.id, article=article.id, run=run.id,
        action=action.id, approval=approval.id, escalation=esc.id,
    )  # fmt: skip


# (repository class, method, kwargs from the world, keyed). A keyed read is given the other
# tenant's ids and must find nothing; an unkeyed list must return only its own tenant's rows.
READS = [
    (customers.CustomerRepository, "get", lambda w: {"id": w.customer}, True),
    (customers.CustomerRepository, "get_by_email", lambda w: {"email": "ada@x.io"}, True),
    (customers.CustomerRepository, "get_many", lambda w: {"ids": [w.customer]}, True),
    (customers.CustomerRepository, "list", lambda w: {}, False),
    (customers.SubscriptionRepository, "get_for_customer", lambda w: {"customer_id": w.customer}, True),  # noqa: E501
    (customers.WorkspaceRepository, "get_for_customer", lambda w: {"customer_id": w.customer}, True),  # noqa: E501
    (profiles.ProfileRepository, "get", lambda w: {"id": w.profile}, True),
    (profiles.ProfileRepository, "get_by_email", lambda w: {"email": "sam@x.io"}, True),
    (profiles.ProfileRepository, "get_first_by_role", lambda w: {"role": "viewer"}, True),
    (tickets.TicketRepository, "get", lambda w: {"id": w.ticket}, True),
    (tickets.TicketRepository, "get_by_number", lambda w: {"ticket_number": "CD-1"}, True),
    (tickets.TicketRepository, "list", lambda w: {}, False),
    (tickets.TicketRepository, "list_for_customer", lambda w: {"customer_id": w.customer}, True),
    (tickets.TicketMessageRepository, "list_for_ticket", lambda w: {"ticket_id": w.ticket}, True),
    (reference.IncidentRepository, "list_active", lambda w: {}, False),
    (reference.ProductRepository, "list", lambda w: {}, False),
    (reference.SupportArticleRepository, "get", lambda w: {"id": w.article}, True),
    (reference.SupportArticleRepository, "list", lambda w: {}, False),
    (workflow.WorkflowRunRepository, "get", lambda w: {"id": w.run}, True),
    (workflow.WorkflowRunRepository, "latest_for_ticket", lambda w: {"ticket_id": w.ticket}, True),
    (workflow.WorkflowRunRepository, "list_recent", lambda w: {}, False),
    (workflow.WorkflowEventRepository, "list_for_ticket", lambda w: {"ticket_id": w.ticket}, True),
    (workflow.WorkflowEventRepository, "list_for_workflow", lambda w: {"workflow_id": w.run}, True),
    (workflow.ResolutionActionRepository, "list_for_ticket", lambda w: {"ticket_id": w.ticket}, True),  # noqa: E501
    (workflow.ResolutionActionRepository, "get_by_idempotency_key", lambda w: {"key": "k1"}, True),
    (approvals.ApprovalRepository, "get", lambda w: {"id": w.approval}, True),
    (approvals.ApprovalRepository, "list", lambda w: {}, False),
    (approvals.ApprovalRepository, "list_expired", lambda w: {"now": NOW}, False),
    (approvals.EscalationRepository, "get", lambda w: {"id": w.escalation}, True),
    (approvals.EscalationRepository, "latest_for_ticket", lambda w: {"ticket_id": w.ticket}, True),
    (approvals.EscalationRepository, "list", lambda w: {}, False),
    (memory.CustomerMemoryRepository, "list_for_customer", lambda w: {"customer_id": w.customer}, True),  # noqa: E501
    (
        memory.CustomerMemoryRepository,
        "exists",
        lambda w: {"customer_id": w.customer, "memory_type": MemoryType.note, "content": "n"},
        True,
    ),
    (audit.AuditLogRepository, "list", lambda w: {}, False),
]  # fmt: skip

# Both tenants hold the same natural key, so the demo tenant finds its own row; it must never be
# the other tenant's (checked by the tenant_id assertion in the test).
NATURAL_KEY_READS = {"get_first_by_role", "get_by_email", "get_by_number", "get_by_idempotency_key"}

# Writes: called through the demo tenant with the other tenant's ids; must report "not found".
WRITES = [
    (tickets.TicketRepository, "update", lambda w: {"id": w.ticket, "status": TicketStatus.closed}),
    (workflow.WorkflowRunRepository, "update", lambda w: {"id": w.run, "current_node": "x"}),
    (
        workflow.ResolutionActionRepository,
        "record_result",
        lambda w: {
            "id": w.action, "status": ResolutionActionStatus.executed,
            "result": {"x": 1}, "verification": None,
        },
    ),
    (
        approvals.ApprovalRepository,
        "decide",
        lambda w: {
            "id": w.approval, "status": ApprovalStatus.approved, "decided_by": "sam", "note": None,
        },
    ),
    (
        approvals.EscalationRepository,
        "update_status",
        lambda w: {"id": w.escalation, "status": EscalationStatus.resolved},
    ),
    (memory.CustomerMemoryRepository, "delete_for_customer", lambda w: {"customer_id": w.customer}),
]  # fmt: skip

CREATES = {
    ("CustomerRepository", "create"), ("SubscriptionRepository", "create"),
    ("WorkspaceRepository", "create"), ("ProfileRepository", "create"),
    ("TicketRepository", "create"), ("TicketMessageRepository", "add"),
    ("IncidentRepository", "create"), ("ProductRepository", "create"),
    ("SupportArticleRepository", "upsert_by_slug"), ("WorkflowRunRepository", "create"),
    ("WorkflowEventRepository", "append"), ("ResolutionActionRepository", "create"),
    ("ApprovalRepository", "create"), ("EscalationRepository", "create"),
    ("CustomerMemoryRepository", "add"), ("AuditLogRepository", "append"),
}  # fmt: skip


# Aggregates return counts, not rows, so they get their own check: the other tenant's data adds 0.
AGGREGATES = [
    (tickets.TicketRepository, "count_open", {}),
    (tickets.TicketRepository, "count_resolved_since", {"since": NOW - timedelta(days=1)}),
    (tickets.TicketRepository, "count_by_severity", {}),
    (tickets.TicketRepository, "count_by_category", {}),
    (tickets.TicketRepository, "resolution_spans", {}),
    (approvals.ApprovalRepository, "count_pending", {}),
    (approvals.EscalationRepository, "count_open", {}),
]


@pytest.fixture
async def worlds(session, tenants):
    mine = await seed_world(session, DEMO_TENANT_ID)
    theirs = await seed_world(session, OTHER_TENANT_ID)
    await session.commit()
    return mine, theirs


def _rows(result):
    """Flatten a read result into a list of rows, whatever shape the method returns."""
    if result is None:
        return []
    if isinstance(result, bool):
        return [result] if result else []
    if isinstance(result, dict):
        return list(result.values())
    if isinstance(result, tuple):
        items, total = result
        assert total == len(items) or items == [] or total >= len(items)
        return list(items)
    return list(result) if isinstance(result, list) else [result]


@pytest.mark.parametrize(
    ("cls", "method", "kwargs", "keyed"), READS, ids=[f"{r[0].__name__}.{r[1]}" for r in READS]
)
async def test_a_second_tenants_rows_are_invisible_to_every_read(
    session, worlds, cls, method, kwargs, keyed
):
    mine, theirs = worlds
    # Positive control: the owning tenant sees the row, so this cannot pass by reading nothing.
    owned = _rows(await getattr(cls(session, OTHER_TENANT_ID), method)(**kwargs(theirs)))
    assert owned, "control failed: the other tenant cannot read its own row"

    seen = await getattr(cls(session, DEMO_TENANT_ID), method)(**kwargs(theirs))
    rows = _rows(seen)
    if keyed and method not in NATURAL_KEY_READS:
        assert rows == [], f"{cls.__name__}.{method} leaked across tenants"
        if isinstance(seen, tuple):
            assert seen[1] == 0
    for row in rows:
        assert row is True or row.tenant_id == DEMO_TENANT_ID


@pytest.mark.parametrize(
    ("cls", "method", "kwargs"), WRITES, ids=[f"{w[0].__name__}.{w[1]}" for w in WRITES]
)
async def test_a_write_cannot_reach_another_tenants_row(session, worlds, cls, method, kwargs):
    _, theirs = worlds
    outcome = await getattr(cls(session, DEMO_TENANT_ID), method)(**kwargs(theirs))
    assert outcome is None or outcome == 0
    await session.commit()
    session.expire_all()
    await _assert_other_tenant_row_unchanged(session, theirs)


async def _assert_other_tenant_row_unchanged(session, w):
    other = OTHER_TENANT_ID
    ticket = await tickets.TicketRepository(session, other).get(w.ticket)
    assert ticket.status == TicketStatus.new
    run = await workflow.WorkflowRunRepository(session, other).get(w.run)
    assert run.current_node is None
    action = await workflow.ResolutionActionRepository(session, other).get_by_idempotency_key("k1")
    assert action.status == ResolutionActionStatus.planned and action.result is None
    approval = await approvals.ApprovalRepository(session, other).get(w.approval)
    assert approval.status == ApprovalStatus.pending and approval.decided_by is None
    esc = await approvals.EscalationRepository(session, other).get(w.escalation)
    assert esc.status == EscalationStatus.open
    notes = await memory.CustomerMemoryRepository(session, other).list_for_customer(w.customer)
    assert len(notes) == 1


def _scoped_classes():
    for info in pkgutil.iter_modules(repos_pkg.__path__):
        mod = importlib.import_module(f"app.repositories.{info.name}")
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ == mod.__name__ and cls is not ScopedRepository:
                yield cls


def test_every_public_repository_method_is_classified():
    known = (
        {(c.__name__, m) for c, m, *_ in READS}
        | {(c.__name__, m) for c, m, _ in WRITES}
        | CREATES
        | {("TicketRepository", "next_ticket_number")}
        | {(c.__name__, m) for c, m, _ in AGGREGATES}
    )
    unclassified = []
    for cls in _scoped_classes():
        if cls is TenantRepository:
            continue
        for name, _fn in inspect.getmembers(cls, inspect.iscoroutinefunction):
            if not name.startswith("_") and (cls.__name__, name) not in known:
                unclassified.append(f"{cls.__name__}.{name}")
    assert unclassified == []


def test_the_tenant_repository_is_the_only_unscoped_one():
    for cls in _scoped_classes():
        if cls is not TenantRepository:
            assert issubclass(cls, ScopedRepository), cls.__name__


async def test_ticket_numbering_ignores_another_tenants_tickets(session, worlds):
    _, theirs = worlds
    other = tickets.TicketRepository(session, OTHER_TENANT_ID)
    await other.create(ticket_number="CD-5000", customer_id=theirs.customer, subject="s", body="b")
    await session.commit()

    assert await tickets.TicketRepository(session, DEMO_TENANT_ID).next_ticket_number() == "CD-1001"
    assert await other.next_ticket_number() == "CD-5001"


@pytest.mark.parametrize(
    ("cls", "method", "kwargs"), AGGREGATES, ids=[f"{a[0].__name__}.{a[1]}" for a in AGGREGATES]
)
async def test_aggregates_count_only_their_own_tenant(session, worlds, cls, method, kwargs):
    mine, _ = worlds
    ticket = await tickets.TicketRepository(session, OTHER_TENANT_ID).get(
        await _other_ticket_id(session)
    )
    ticket.severity, ticket.category = "high", Category.billing
    ticket.status, ticket.resolved_at = TicketStatus.resolved, NOW
    await session.commit()

    owner = await getattr(cls(session, OTHER_TENANT_ID), method)(**kwargs)
    seen = await getattr(cls(session, DEMO_TENANT_ID), method)(**kwargs)

    if method in {"count_pending", "count_open"} and cls is approvals.ApprovalRepository:
        assert owner == 1 and seen == 1  # one pending approval each: neither sees the other's
    elif method == "count_open" and cls is approvals.EscalationRepository:
        assert owner == 1 and seen == 1
    elif method == "count_open":
        assert owner == 0 and seen == 1  # their ticket is resolved; mine is still open
    elif method == "count_resolved_since":
        assert owner == 1 and seen == 0
    elif method in {"count_by_severity", "count_by_category"}:
        assert sum(owner.values()) == 1 and seen == {}
    else:
        assert len(owner) == 1 and seen == []


async def _other_ticket_id(session) -> str:
    rows, _ = await tickets.TicketRepository(session, OTHER_TENANT_ID).list()
    return rows[0].id
