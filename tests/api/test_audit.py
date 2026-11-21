"""P3-4 (N6): every non-GET request writes one audit row; the middleware order is fixed."""

import asyncio
import logging

import pytest
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import get_sessionmaker
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.repositories.audit import AuditLogRepository

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")


def _rows() -> list:
    async def read():
        async with get_sessionmaker()() as session:
            rows, _ = await AuditLogRepository(session).list(page_size=100)
            return rows

    return asyncio.run(read())


def test_non_get_request_writes_a_row_with_actor_and_request_id(client, agent_headers):
    response = client.post(
        "/api/v1/tickets/abc/reply",
        headers={**agent_headers, "X-Request-ID": "req-123"},
        json={"body": "do not log me: hunter2"},
    )

    assert response.status_code == 404
    rows = [r for r in _rows() if r.request_id == "req-123"]
    assert len(rows) == 1
    row = rows[0]
    assert row.actor == "sam.agent@clouddesk.demo"
    assert row.actor_type == "user"
    assert row.action == "POST /api/v1/tickets/abc/reply"
    assert (row.resource_type, row.resource_id) == ("tickets", "abc")
    assert row.details["status_code"] == 404
    assert "hunter2" not in str(row.details)


def test_missing_or_invalid_token_is_anonymous(client):
    client.post("/api/v1/nothing", headers={"X-Request-ID": "anon-1"})
    client.post(
        "/api/v1/nothing",
        headers={"X-Request-ID": "anon-2", "Authorization": "Bearer not-a-jwt"},
    )

    rows = {r.request_id: r for r in _rows()}
    for rid in ("anon-1", "anon-2"):
        assert rows[rid].actor == "anonymous"
        assert rows[rid].actor_type == "anonymous"


def test_get_requests_write_no_row(client, agent_headers):
    client.get("/health/live", headers={"X-Request-ID": "get-1"})
    client.get("/api/v1/auth/me", headers={**agent_headers, "X-Request-ID": "get-2"})

    assert [r for r in _rows() if r.request_id in ("get-1", "get-2")] == []


def test_a_failing_audit_write_never_breaks_the_response(client, monkeypatch, caplog):
    async def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(AuditLogRepository, "append", boom)
    with caplog.at_level(logging.ERROR):
        response = client.post("/api/v1/nothing", headers={"X-Request-ID": "fail-1"})

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "fail-1"
    assert any("audit" in r.getMessage() for r in caplog.records)


def test_middleware_order_is_cors_request_id_rate_limit_audit(client):
    # user_middleware lists outermost first.
    order = [m.cls for m in client.app.user_middleware]
    assert order == [CORSMiddleware, RequestIdMiddleware, RateLimitMiddleware, AuditMiddleware]
