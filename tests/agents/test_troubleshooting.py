"""P9-5: the Troubleshooting agent returns causes and numbered steps, with playbook and status."""

import re

from agents.specialists.troubleshooting import PLAYBOOKS, TroubleshootingAgent, number_steps
from app.schemas.common import Category
from app.schemas.workflow import Classification
from app.tools.factory import build_read_registry


def _cls(category):
    return Classification(category=category, summary="s", confidence=0.9)


async def test_diagnosis_has_causes_and_numbered_steps(tool_env, text_of):
    agent = TroubleshootingAgent(build_read_registry(tool_env))
    d, status, usage, ms, calls = await agent.run(
        text_of("CD-1003"), _cls(Category.api_failure), []
    )
    assert status == "ok" and d.probable_causes and d.troubleshooting_steps
    assert all(re.match(rf"{n}\. \S", s) for n, s in enumerate(d.troubleshooting_steps, 1))
    assert any("rate limit" in c.lower() for c in d.probable_causes)  # playbook enrichment
    assert usage.estimated_cost_usd == 0.0


async def test_active_incident_becomes_the_first_cause(tool_env, text_of):
    agent = TroubleshootingAgent(build_read_registry(tool_env))
    d, _, _, _, calls = await agent.run(text_of("CD-1001"), _cls(Category.login_issue), [])
    assert [c.name for c in calls] == ["check_service_status"]
    assert calls[0].args == {"service": "sso"}
    assert d.probable_causes[0].startswith("Active incident: SSO login failures")


async def test_no_status_check_for_categories_without_a_service(tool_env, text_of):
    agent = TroubleshootingAgent(build_read_registry(tool_env))
    _, _, _, _, calls = await agent.run(text_of("CD-1002"), _cls(Category.billing), [])
    assert calls == []


async def test_model_failure_falls_back_to_playbook(tool_env):
    class Broken:
        name = "x"
        model = "x"

        def estimate_cost(self, *_):
            return 0.0

        async def complete(self, *a):
            raise RuntimeError("down")

    agent = TroubleshootingAgent(build_read_registry(tool_env), Broken())
    d, status, *_ = await agent.run("t", _cls(Category.storage_quota), [])
    assert status == "fallback" and d.troubleshooting_steps[0].startswith("1. ")
    assert len(d.troubleshooting_steps) == len(PLAYBOOKS[Category.storage_quota][1])


def test_every_category_has_a_playbook_and_numbering_is_idempotent():
    assert set(PLAYBOOKS) == set(Category)
    assert number_steps(["1. a", "- b", "  "]) == ["1. a", "2. b"]
