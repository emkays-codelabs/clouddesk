"""P9-7 (F10): policy rules always escalate; vague model escalations are distrusted."""

from uuid import uuid4

import pytest
import sqlalchemy as sa

from agents.specialists.escalation import DEFAULT_TEAM, EscalationAgent
from app.core.llm import Completion
from app.models.entities import Escalation, Ticket
from app.repositories.workflow import WorkflowRunRepository
from app.schemas.common import Category, Severity
from app.schemas.workflow import Classification
from app.tools.factory import build_default_registry

PLANS = {
    "CD-1005": "business",
    "CD-1006": "enterprise",
    "CD-1009": "pro",
    "CD-1011": "pro",
    "CD-1002": "business",
    "CD-1010": "free",
}


class Scripted:
    name = "scripted"
    model = "scripted"

    def __init__(self, text="{}"):
        self.text = text

    def estimate_cost(self, *_):
        return 0.0

    async def complete(self, schema, messages, temperature, hints):
        return Completion(self.text, 1, 1)


def _decision(escalate, confidence, team="Security team"):
    return (
        f'{{"escalation_required":{str(escalate).lower()},"reason":"r",'
        f'"assigned_team":"{team}","priority":"high","confidence":{confidence}}}'
    )


def _cls(category=Category.other):
    return Classification(category=category, summary="s", confidence=0.9)


async def _ticket_id(env, number):
    async with env.session_factory() as s:
        stmt = sa.select(Ticket.id).where(Ticket.ticket_number == number)
        return (await s.execute(stmt)).scalar_one()


async def _escalations(env, tid):
    async with env.session_factory() as s:
        stmt = sa.select(Escalation).where(Escalation.ticket_id == tid)
        return (await s.execute(stmt)).all()


async def _run(env, number, text_of, llm, severity=Severity.medium):
    tid = await _ticket_id(env, number)
    async with env.session_factory() as s:
        run = await WorkflowRunRepository(s).create(ticket_id=tid, thread_id=f"th-{uuid4().hex}")
        await s.commit()
    agent = EscalationAgent(build_default_registry(env), llm)
    out = await agent.run(tid, text_of(number), PLANS[number], _cls(), severity, workflow_id=run.id)
    return tid, out


@pytest.mark.parametrize(
    "number,team",
    [
        ("CD-1005", "Security team"),
        ("CD-1006", "Data protection team"),
        ("CD-1009", "Privacy team"),
        ("CD-1011", "Billing disputes team"),
    ],
)
async def test_policy_cases_escalate_to_their_team_without_a_model_call(
    tool_env, text_of, monkeypatch, number, team
):
    async def boom(*a, **k):
        raise AssertionError("model called")

    monkeypatch.setattr("agents.specialists.escalation.call_structured", boom)
    tid, (decision, status, usage, ms, calls) = await _run(
        tool_env, number, text_of, Scripted(_decision(False, 0.99))
    )
    assert decision.escalation_required and decision.assigned_team == team
    assert status == "ok" and usage.total_tokens == 0
    assert [c.name for c in calls] == ["create_escalation"] and calls[0].ok
    assert len(await _escalations(tool_env, tid)) == 1


async def test_policy_wins_even_when_the_model_would_decline(tool_env, text_of):
    _, (decision, *_) = await _run(
        tool_env, "CD-1011", text_of, Scripted(_decision(False, 0.99)), Severity.low
    )
    assert decision.escalation_required


async def test_low_confidence_model_escalation_on_a_benign_ticket_does_not_escalate(
    tool_env, text_of
):
    tid, (decision, status, usage, ms, calls) = await _run(
        tool_env, "CD-1010", text_of, Scripted(_decision(True, 0.4)), Severity.low
    )
    assert not decision.escalation_required and calls == []
    assert await _escalations(tool_env, tid) == []


async def test_confident_model_escalation_below_high_severity_is_distrusted(tool_env, text_of):
    _, (decision, *_) = await _run(
        tool_env, "CD-1010", text_of, Scripted(_decision(True, 0.9)), Severity.medium
    )
    assert not decision.escalation_required


async def test_confident_model_escalation_at_high_severity_is_kept(tool_env, text_of):
    _, (decision, _, _, _, calls) = await _run(
        tool_env, "CD-1002", text_of, Scripted(_decision(True, 0.9, "Tier 2")), Severity.high
    )
    assert decision.escalation_required and decision.assigned_team == "Tier 2"
    assert [c.name for c in calls] == ["create_escalation"]


async def test_low_confidence_at_high_severity_escalates_to_the_default_team(tool_env, text_of):
    _, (decision, *_) = await _run(
        tool_env, "CD-1002", text_of, Scripted(_decision(False, 0.4)), Severity.high
    )
    assert decision.escalation_required and decision.assigned_team == DEFAULT_TEAM


async def test_model_failure_on_a_benign_ticket_does_not_escalate(tool_env, text_of):
    class Broken(Scripted):
        async def complete(self, *a):
            raise RuntimeError("down")

    _, (decision, status, *_) = await _run(tool_env, "CD-1010", text_of, Broken(), Severity.low)
    assert status == "fallback" and not decision.escalation_required


async def test_the_escalation_is_idempotent_on_retry(tool_env, text_of):
    tid, _ = await _run(tool_env, "CD-1005", text_of, Scripted())
    await _run(tool_env, "CD-1005", text_of, Scripted())
    assert len(await _escalations(tool_env, tid)) == 1


def test_the_default_team_is_spelled_the_same_in_the_agent_and_the_ticket_service():
    from agents.specialists.escalation import DEFAULT_TEAM
    from app.services.ticket_service import DEFAULT_ESCALATION_TEAM

    assert DEFAULT_ESCALATION_TEAM == DEFAULT_TEAM == "Tier 2 support"
