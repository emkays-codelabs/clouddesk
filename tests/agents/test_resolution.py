"""P9-6 (F8, F9, N5): the Resolution agent plans actions by rule and grounds a validated reply."""

import pytest

from agents.specialists.customer import CustomerAgent
from agents.specialists.knowledge import KnowledgeAgent
from agents.specialists.resolution import (
    VALIDATION_FAILED_MARKER,
    ResolutionAgent,
    reply_failed_validation,
    trusted_values,
)
from agents.specialists.troubleshooting import TroubleshootingAgent
from app.core.config import get_settings
from app.core.llm import Completion
from app.core.output_validation import validate_customer_output
from app.schemas.common import Category
from app.schemas.workflow import Classification, Diagnosis, Evidence
from app.tools.factory import build_read_registry
from app.tools.policy import ToolPolicy

CUSTOMER_KEYS = {
    "CD-1001": "cust-northwind",
    "CD-1002": "cust-brightpath",
    "CD-1010": "cust-juniper",
    "CD-1011": "cust-pixelforge",
}


def _cls(category):
    return Classification(category=category, summary="s", confidence=0.9)


async def _context(tool_env, seed_id, number):
    agent = CustomerAgent(tool_env, build_read_registry(tool_env))
    ctx, *_ = await agent.run(seed_id("customer", CUSTOMER_KEYS[number]))
    return ctx


def _agent(llm=None):
    return ResolutionAgent(get_settings(), llm)


class Scripted:
    name = "scripted"
    model = "scripted"

    def __init__(self, text):
        self.text = text

    def estimate_cost(self, *_):
        return 0.0

    async def complete(self, schema, messages, temperature, hints):
        return Completion(self.text, 1, 1)


async def _diagnose(tool_env, text, category):
    registry = build_read_registry(tool_env)
    evidence, *_ = await KnowledgeAgent(registry).run(text)
    diag, *_ = await TroubleshootingAgent(registry).run(text, _cls(category), evidence)
    return evidence, diag


async def test_refund_ticket_plans_one_approval_gated_refund_from_context(
    tool_env, seed_id, text_of
):
    ctx = await _context(tool_env, seed_id, "CD-1002")
    plan = _agent().plan_actions("tid-1", text_of("CD-1002"), Category.billing, ctx)
    refunds = [a for a in plan if a.tool == "create_refund_request"]
    assert len(refunds) == 1
    r = refunds[0]
    assert r.requires_approval is True
    assert r.arguments["customer_id"] == ctx.customer.id
    assert r.arguments["subscription_id"] == ctx.subscription.id
    assert r.arguments["amount"] == 75.0  # 3 unused seats at 200 / 8
    assert r.arguments["amount"] in trusted_values(ctx)
    assert all(a.tool in {"update_ticket", "create_refund_request"} for a in plan)


async def test_amount_in_ticket_text_is_never_used(tool_env, seed_id):
    ctx = await _context(tool_env, seed_id, "CD-1002")
    text = "Please refund $9999 of my seats. We were billed for 8 seats but use 5."
    plan = _agent().plan_actions("tid-1", text, Category.billing, ctx)
    amounts = [a.arguments["amount"] for a in plan if a.tool == "create_refund_request"]
    assert amounts == [75.0]


async def test_escalated_billing_plans_no_actions(tool_env, seed_id, text_of):
    ctx = await _context(tool_env, seed_id, "CD-1011")
    plan = _agent().plan_actions("tid-2", text_of("CD-1011"), Category.billing, ctx)
    assert plan == []


async def test_non_refund_tickets_get_only_a_status_update(tool_env, seed_id, text_of):
    ctx = await _context(tool_env, seed_id, "CD-1010")
    plan = _agent().plan_actions("tid-3", text_of("CD-1010"), Category.feature_request, ctx)
    assert [a.tool for a in plan] == ["update_ticket"]
    assert plan[0].requires_approval is False


async def test_reset_only_when_the_ticket_asks_for_a_setting_reset(tool_env, seed_id):
    ctx = await _context(tool_env, seed_id, "CD-1001")
    ask = "Please reset the SSO setting for our workspace, it is stuck."
    plan = _agent().plan_actions("tid-4", ask, Category.login_issue, ctx)
    reset = [a for a in plan if a.tool == "reset_demo_setting"]
    assert len(reset) == 1 and reset[0].requires_approval is True
    assert reset[0].arguments == {"workspace_id": ctx.workspace.id, "setting": "sso"}
    plain = _agent().plan_actions("tid-4", "SSO login fails", Category.login_issue, ctx)
    assert not [a for a in plain if a.tool == "reset_demo_setting"]


async def test_run_actions_equal_plan_actions_and_model_cannot_add_any(tool_env, seed_id, text_of):
    ctx = await _context(tool_env, seed_id, "CD-1002")
    text = text_of("CD-1002")
    ev, diag = await _diagnose(tool_env, text, Category.billing)
    sneaky = (
        '{"summary":"s","customer_response":"Refund done.","internal_notes":"",'
        '"actions":[{"tool":"create_refund_request","arguments":{"amount":99999},'
        '"requires_approval":false}]}'
    )
    agent = _agent(Scripted(sneaky))
    plan, status, usage, ms, calls = await agent.run(
        "tid-5", text, _cls(Category.billing), ctx, ev, diag
    )
    assert plan.actions == agent.plan_actions("tid-5", text, Category.billing, ctx)
    assert all(a.arguments.get("amount") != 99999 for a in plan.actions)
    assert calls == []


async def test_reply_is_grounded_and_passes_validation(tool_env, seed_id, text_of):
    ctx = await _context(tool_env, seed_id, "CD-1002")
    text = text_of("CD-1002")
    ev, diag = await _diagnose(tool_env, text, Category.billing)
    plan, status, usage, ms, _ = await _agent().run(
        "tid-6", text, _cls(Category.billing), ctx, ev, diag
    )
    assert status == "ok" and usage.estimated_cost_usd == 0.0
    result = validate_customer_output(plan.customer_response, [*ev, *diag.troubleshooting_steps])
    assert result.ok and result.groundedness >= 0.8
    assert not reply_failed_validation(plan)
    assert diag.troubleshooting_steps[0].split(". ", 1)[1] in plan.customer_response
    assert ev[0].title in plan.customer_response  # the reply cites its article
    assert "kb://" not in plan.customer_response


async def test_ungrounded_model_reply_is_replaced_by_the_grounded_one(tool_env, seed_id, text_of):
    ctx = await _context(tool_env, seed_id, "CD-1002")
    text = text_of("CD-1002")
    ev, diag = await _diagnose(tool_env, text, Category.billing)
    wild = (
        '{"summary":"s","customer_response":"Your account is premium platinum forever and we '
        'guarantee unlimited compensation payments immediately.","internal_notes":"","actions":[]}'
    )
    plan, *_ = await _agent(Scripted(wild)).run(
        "tid-7", text, _cls(Category.billing), ctx, ev, diag
    )
    assert "platinum" not in plan.customer_response
    assert validate_customer_output(plan.customer_response, [*ev, *diag.troubleshooting_steps]).ok


async def test_a_leaking_reply_is_withheld_and_flagged_for_escalation(tool_env, seed_id, text_of):
    ctx = await _context(tool_env, seed_id, "CD-1002")
    leaky = Evidence(
        id="x",
        title="Internal",
        source="kb://x",
        snippet="Open http://localhost:8000/admin",
        score=1,
    )
    bad_diag = Diagnosis(
        problem="p", troubleshooting_steps=["1. Open http://localhost:8000/admin to check"]
    )
    plan, *_ = await _agent().run(
        "tid-8", text_of("CD-1002"), _cls(Category.billing), ctx, [leaky], bad_diag
    )
    assert reply_failed_validation(plan) and VALIDATION_FAILED_MARKER in plan.internal_notes
    assert "localhost" not in plan.customer_response


async def test_model_failure_falls_back_to_the_grounded_reply(tool_env, seed_id, text_of):
    class Broken(Scripted):
        async def complete(self, *a):
            raise RuntimeError("down")

    ctx = await _context(tool_env, seed_id, "CD-1002")
    text = text_of("CD-1002")
    ev, diag = await _diagnose(tool_env, text, Category.billing)
    plan, status, *_ = await _agent(Broken("")).run(
        "tid-9", text, _cls(Category.billing), ctx, ev, diag
    )
    assert status == "fallback" and plan.customer_response and plan.actions
    assert not reply_failed_validation(plan)


async def test_ticket_and_kb_text_reach_the_model_only_wrapped(tool_env, seed_id, text_of):
    seen = []

    class Spy(Scripted):
        async def complete(self, schema, messages, temperature, hints):
            seen.append(messages[-1]["content"])
            return await super().complete(schema, messages, temperature, hints)

    ctx = await _context(tool_env, seed_id, "CD-1002")
    text = text_of("CD-1002")
    ev, diag = await _diagnose(tool_env, text, Category.billing)
    ok = '{"summary":"s","customer_response":"Hi.","internal_notes":"","actions":[]}'
    await _agent(Spy(ok)).run("tid-10", text, _cls(Category.billing), ctx, ev, diag)
    user = seen[0]
    assert user.count("<untrusted_content>") == user.count("</untrusted_content>") >= 2
    assert user.index("refund the 3 unused seats") > user.index("<untrusted_content>")


@pytest.mark.parametrize("number", ["CD-1001", "CD-1010", "CD-1002"])
async def test_plan_carries_policy_flags_for_every_action(tool_env, seed_id, text_of, number):
    ctx = await _context(tool_env, seed_id, number)
    plan = _agent().plan_actions("t", text_of(number), Category.billing, ctx)
    policy = ToolPolicy(get_settings())
    assert plan and all(
        a.requires_approval == policy.requires_approval(a.tool, a.arguments) for a in plan
    )
