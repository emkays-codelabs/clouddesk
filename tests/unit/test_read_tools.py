"""P6-2: read-only tools run through the registry, return documented shapes, never write."""

import sqlalchemy as sa

from app.models.entities import AuditLog, Customer, Escalation, ResolutionAction, Ticket
from app.tools.factory import READ_TOOL_NAMES, build_read_registry
from app.tools.read_tools import build_read_tools


async def _counts(ctx):
    async with ctx.session_factory() as s:
        out = {}
        for model in (Customer, Ticket, Escalation, ResolutionAction, AuditLog):
            out[model.__name__] = (
                await s.execute(sa.select(sa.func.count()).select_from(model))
            ).scalar_one()
        return out


def test_builder_returns_the_five_documented_tools_with_docstrings(tool_env):
    tools = build_read_tools(tool_env)
    assert sorted(t.__name__ for t in tools) == sorted(READ_TOOL_NAMES)
    assert set(READ_TOOL_NAMES) == {
        "get_customer",
        "get_subscription",
        "get_ticket_history",
        "search_docs",
        "check_service_status",
    }
    assert all(t.__doc__ and t.__doc__.strip() for t in tools)


def test_registry_lists_read_tools_without_approval(tool_env):
    reg = build_read_registry(tool_env)
    listed = {t["name"]: t for t in reg.list_tools()}
    assert set(listed) == set(READ_TOOL_NAMES)
    assert all(t["requires_approval"] is False and t["description"] for t in listed.values())


async def test_get_customer_shape(tool_env, seed_id):
    reg = build_read_registry(tool_env)
    cid = seed_id("customer", "cust-northwind")
    res = await reg.execute("get_customer", {"customer_id": cid})
    assert res.ok
    created_at = res.data.pop("created_at")
    assert isinstance(created_at, str)
    assert res.data == {
        "id": cid,
        "name": "Priya Raman",
        "email": "priya.raman@northwind.example",
        "company": "Northwind Logistics",
        "plan_name": "enterprise",
        "status": "active",
        "region": "eu-west",
        "lifetime_value": 184000.0,
    }


async def test_get_customer_unknown_is_a_failed_result_not_a_crash(tool_env):
    res = await build_read_registry(tool_env).execute("get_customer", {"customer_id": "nope"})
    assert not res.ok and "not found" in res.error


async def test_get_subscription_shape(tool_env, seed_id):
    cid = seed_id("customer", "cust-northwind")
    res = await build_read_registry(tool_env).execute("get_subscription", {"customer_id": cid})
    assert res.ok
    d = res.data
    assert d["id"] == seed_id("subscription", "cust-northwind")
    assert d["customer_id"] == cid and d["plan"] == "enterprise" and d["seats"] == 120
    assert d["mrr"] == 6000.0 and d["storage_quota_gb"] == 5000.0 and d["api_rate_limit"] == 10000
    assert isinstance(d["renews_at"], str) and d["renews_at"].startswith("2027-03-01")


async def test_get_subscription_unknown_customer_fails(tool_env):
    res = await build_read_registry(tool_env).execute("get_subscription", {"customer_id": "nope"})
    assert not res.ok and "not found" in res.error


async def test_get_ticket_history_excludes_current_and_is_plain_data(tool_env, seed_id):
    reg = build_read_registry(tool_env)
    ticket = None
    async with tool_env.session_factory() as s:
        ticket = (await s.execute(sa.select(Ticket).limit(1))).scalar_one()
    res = await reg.execute(
        "get_ticket_history",
        {"customer_id": ticket.customer_id, "exclude_ticket_id": ticket.id, "limit": 5},
    )
    assert res.ok and isinstance(res.data, list)
    assert all(t["id"] != ticket.id for t in res.data)
    for item in res.data:
        assert set(item) == {
            "id",
            "ticket_number",
            "subject",
            "status",
            "severity",
            "category",
            "channel",
            "escalation_required",
            "created_at",
            "updated_at",
        }
        assert isinstance(item["created_at"], str)


async def test_search_docs_returns_cited_evidence(tool_env):
    res = await build_read_registry(tool_env).execute(
        "search_docs", {"query": "SAML single sign-on login fails", "top_k": 3}
    )
    assert res.ok and 1 <= len(res.data) <= 3
    first = res.data[0]
    assert {"id", "title", "source", "snippet", "score", "article_id"} <= set(first)
    assert first["source"].startswith("kb://")


async def test_search_docs_is_not_cached_as_an_action(tool_env):
    reg = build_read_registry(tool_env)
    a = await reg.execute("search_docs", {"query": "refund seats"})
    b = await reg.execute("search_docs", {"query": "refund seats"})
    assert a.ok and b.ok and b.idempotent is False


async def test_check_service_status_lists_active_incidents(tool_env):
    reg = build_read_registry(tool_env)
    res = await reg.execute("check_service_status", {})
    assert res.ok and res.data["status"] == "degraded"
    titles = [i["title"] for i in res.data["incidents"]]
    assert "SSO login failures for SAML customers" in titles
    assert "Elevated API latency in us-east" not in titles  # resolved
    assert set(res.data["incidents"][0]) == {
        "id",
        "title",
        "status",
        "severity",
        "affected_services",
        "description",
    }


async def test_check_service_status_filters_by_service(tool_env):
    reg = build_read_registry(tool_env)
    sso = await reg.execute("check_service_status", {"service": "SSO"})
    assert sso.data["status"] == "degraded" and len(sso.data["incidents"]) == 1
    storage = await reg.execute("check_service_status", {"service": "storage"})
    assert storage.data == {"status": "operational", "service": "storage", "incidents": []}


async def test_no_read_tool_writes(tool_env, seed_id):
    reg = build_read_registry(tool_env)
    before = await _counts(tool_env)
    cid = seed_id("customer", "cust-northwind")
    await reg.execute("get_customer", {"customer_id": cid})
    await reg.execute("get_subscription", {"customer_id": cid})
    await reg.execute("get_ticket_history", {"customer_id": cid})
    await reg.execute("search_docs", {"query": "mfa locked out"})
    await reg.execute("check_service_status", {})
    assert await _counts(tool_env) == before
