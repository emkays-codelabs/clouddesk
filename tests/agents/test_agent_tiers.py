"""P9-9 (F14): each specialist asks for its own model tier.

Supervisor `fast`, Resolution and Escalation `smart`, Troubleshooting `reasoning`. The fake
provider answers (it ignores tiers), so the test spies on `call_structured` to see the tier asked.
"""

import pytest

from agents.specialists import escalation, resolution, supervisor, troubleshooting
from agents.specialists.customer import CustomerAgent
from agents.specialists.escalation import EscalationAgent
from agents.specialists.knowledge import KnowledgeAgent
from agents.specialists.resolution import ResolutionAgent
from agents.specialists.supervisor import SupervisorAgent
from agents.specialists.troubleshooting import TroubleshootingAgent
from app.core import llm
from app.core.config import get_settings
from app.schemas.common import Category, Severity
from app.schemas.workflow import Classification
from app.tools.factory import build_default_registry, build_read_registry


@pytest.fixture
def asked(monkeypatch):
    seen: list[tuple[str, str]] = []
    real = llm.call_structured

    async def spy(schema, **kwargs):
        seen.append((schema.__name__, kwargs.get("tier", "<default>")))
        return await real(schema, **kwargs)

    for module in (supervisor, resolution, escalation, troubleshooting):
        monkeypatch.setattr(module, "call_structured", spy)
    return seen


def _cls(category):
    return Classification(category=category, summary="s", confidence=0.9)


async def test_supervisor_uses_the_fast_tier(asked, text_of):
    await SupervisorAgent().understand(text_of("CD-1010"))
    await SupervisorAgent().assess_severity(text_of("CD-1010"))
    assert asked == [("Classification", "fast"), ("SeverityAssessment", "fast")]


async def test_troubleshooting_uses_the_reasoning_tier(asked, tool_env, text_of):
    await TroubleshootingAgent(build_read_registry(tool_env)).run(
        text_of("CD-1003"), _cls(Category.api_failure), []
    )
    assert asked == [("Diagnosis", "reasoning")]


async def test_resolution_uses_the_smart_tier(asked, tool_env, seed_id, text_of):
    registry = build_read_registry(tool_env)
    context, *_ = await CustomerAgent(tool_env, registry).run(seed_id("customer", "cust-juniper"))
    text = text_of("CD-1010")
    evidence, *_ = await KnowledgeAgent(registry).run(text)
    diagnosis, *_ = await TroubleshootingAgent(registry).run(
        text, _cls(Category.feature_request), evidence
    )
    asked.clear()
    await ResolutionAgent(get_settings()).run(
        "t-1", text, _cls(Category.feature_request), context, evidence, diagnosis
    )
    assert asked == [("ResolutionPlan", "smart")]


async def test_escalation_uses_the_smart_tier_when_no_policy_rule_matched(asked, tool_env, text_of):
    agent = EscalationAgent(build_default_registry(tool_env))
    await agent.run("t-1", text_of("CD-1010"), "pro", _cls(Category.feature_request), Severity.low)
    assert asked == [("EscalationDecision", "smart")]
