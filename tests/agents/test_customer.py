"""P9-3: the Customer agent builds a full context from tools and memory, with no model call."""

import pytest
import sqlalchemy as sa

import app.core.llm as llm_mod
from agents.specialists.customer import CustomerAgent
from app.models.entities import Ticket
from app.services.customer_memory_service import build_memory_service
from app.tools.factory import build_read_registry


async def test_known_customer_returns_full_context_without_a_model_call(
    tool_env, seed_id, monkeypatch
):
    async def boom(*a, **k):
        raise AssertionError("model called")

    monkeypatch.setattr(llm_mod, "call_structured", boom)
    cid = seed_id("customer", "cust-northwind")
    agent = CustomerAgent(tool_env, build_read_registry(tool_env))
    ctx, status, usage, ms, calls = await agent.run(cid)
    assert status == "ok" and usage.total_tokens == 0 and ms >= 0
    assert ctx.customer.name == "Priya Raman" and ctx.customer.plan_name == "enterprise"
    assert ctx.subscription and ctx.subscription.seats == 120
    assert ctx.workspace is not None
    assert [c.name for c in calls] == ["get_customer", "get_subscription", "get_ticket_history"]
    assert all(c.ok for c in calls)


async def test_history_excludes_the_current_ticket(tool_env, seed_id):
    cid = seed_id("customer", "cust-northwind")
    async with tool_env.session_factory() as s:
        stmt = sa.select(Ticket.id).where(Ticket.customer_id == cid)
        tid = (await s.execute(stmt)).scalars().first()
    agent = CustomerAgent(tool_env, build_read_registry(tool_env))
    ctx, *_ = await agent.run(cid, tid)
    assert all(t.id != tid for t in ctx.previous_tickets)


async def test_memory_notes_are_recalled_up_to_ten(tool_env, seed_id):
    cid = seed_id("customer", "cust-brightpath")
    async with tool_env.session_factory() as s:
        svc = build_memory_service(s)
        for n in range(14):
            await svc._long_term.remember(cid, "note", f"distinct note {n}", 0.9)
        await s.commit()
    agent = CustomerAgent(tool_env, build_read_registry(tool_env))
    ctx, *_ = await agent.run(cid)
    assert 1 <= len(ctx.memory_notes) <= 10
    assert all(n.startswith("note: ") for n in ctx.memory_notes)


async def test_unknown_customer_raises_lookup_error(tool_env):
    agent = CustomerAgent(tool_env, build_read_registry(tool_env))
    with pytest.raises(LookupError):
        await agent.run("no-such-customer")
