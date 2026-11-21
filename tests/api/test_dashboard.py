"""P4-5 (F12): GET /dashboard/summary matches the contract and counts from the database."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.database import get_sessionmaker
from app.repositories.approvals import EscalationRepository
from app.repositories.tickets import TicketRepository
from app.schemas.common import Severity, TicketStatus

pytestmark = [
    pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning"),
    pytest.mark.usefixtures("fresh_db"),
]

SUMMARY = "/api/v1/dashboard/summary"


def _ticket_ids(client, headers) -> dict[str, str]:
    params = {"page_size": 100}
    items = client.get("/api/v1/tickets", headers=headers, params=params).json()["items"]
    return {t["ticket_number"]: t["id"] for t in items}


def _update(ticket_id: str, **fields) -> None:
    async def run():
        async with get_sessionmaker()() as session:
            await TicketRepository(session).update(ticket_id, **fields)
            await session.commit()

    asyncio.run(run())


def _escalate(ticket_id: str) -> None:
    async def run():
        async with get_sessionmaker()() as session:
            await EscalationRepository(session).create(ticket_id=ticket_id, reason="r")
            await session.commit()

    asyncio.run(run())


def test_unauthenticated_gets_401(client):
    assert client.get(SUMMARY).status_code == 401


def test_every_role_can_read_and_the_shape_matches_the_contract(
    client, viewer_headers, agent_headers, admin_headers
):
    for headers in (viewer_headers, agent_headers, admin_headers):
        response = client.get(SUMMARY, headers=headers)
        assert response.status_code == 200
        assert set(response.json()) == {
            "open_tickets",
            "resolved_today",
            "pending_approvals",
            "escalations_open",
            "avg_resolution_minutes",
            "by_severity",
            "by_category",
            "recent_tickets",
            "agent_activity",
        }


def test_fresh_demo_data_counts(client, viewer_headers):
    body = client.get(SUMMARY, headers=viewer_headers).json()

    assert body["open_tickets"] == 13
    assert body["resolved_today"] == 0
    assert body["pending_approvals"] == 0
    assert body["escalations_open"] == 0
    assert body["avg_resolution_minutes"] == 0
    assert body["by_severity"] == {"low": 0, "medium": 0, "high": 0, "critical": 0}
    assert set(body["by_category"].values()) == {0}
    assert len(body["by_category"]) == 10
    assert len(body["recent_tickets"]) == 5
    assert body["recent_tickets"][0]["customer_name"]
    assert body["agent_activity"] == []


def test_counts_follow_ticket_state(client, viewer_headers):
    ids = _ticket_ids(client, viewer_headers)
    now = datetime.now(UTC)
    _update(ids["CD-1001"], severity=Severity.critical, category="login_issue")
    _update(ids["CD-1002"], severity=Severity.high, category="billing", approval_status="pending")
    _update(ids["CD-1003"], severity=Severity.high)
    _update(
        ids["CD-1004"],
        status=TicketStatus.resolved,
        created_at=now - timedelta(minutes=90),
        resolved_at=now - timedelta(minutes=30),
    )
    _update(
        ids["CD-1005"],
        status=TicketStatus.closed,
        created_at=now - timedelta(days=3, minutes=20),
        resolved_at=now - timedelta(days=3),
    )
    _escalate(ids["CD-1005"])

    body = client.get(SUMMARY, headers=viewer_headers).json()

    assert body["open_tickets"] == 11
    assert body["resolved_today"] == 1
    assert body["escalations_open"] == 1
    assert body["by_severity"] == {"low": 0, "medium": 0, "high": 2, "critical": 1}
    assert body["by_category"]["login_issue"] == 1 and body["by_category"]["billing"] == 1
    assert body["avg_resolution_minutes"] == pytest.approx(40.0, abs=0.1)
