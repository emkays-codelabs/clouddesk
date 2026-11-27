"""P9-5 (F7): the Troubleshooting agent returns causes and numbered steps."""

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


# --- QA defect: playbook steps that only restate a model step were appended as duplicates ---

from agents.specialists.troubleshooting import is_duplicate_step, merge_steps  # noqa: E402

MODEL_BILLING = [
    "1. Compare the billed seat count with the active workspace member count",
    "2. Review the last invoices for duplicates or mis-timed charges",
    "3. Prepare a refund request for the unused seats for human approval",
]


def test_an_exact_restatement_is_a_duplicate_ignoring_case_and_numbering():
    assert is_duplicate_step("Confirm the token is valid", "2. confirm the TOKEN is valid.")


def test_a_paraphrase_that_adds_words_is_a_duplicate():
    assert is_duplicate_step("Compare billed seats with active workspace members", MODEL_BILLING[0])
    assert is_duplicate_step("Review the last invoices for duplicates", MODEL_BILLING[1])
    assert is_duplicate_step("Prepare any refund request for human approval", MODEL_BILLING[2])


def test_materially_different_steps_are_not_duplicates():
    assert not is_duplicate_step(
        "Add backoff and retry to the client", "Confirm the token is valid"
    )
    assert not is_duplicate_step(
        "Check the request rate against the plan's API limit", "Check the token has not expired"
    )
    # Same opening verb, different object: a different diagnostic action.
    assert not is_duplicate_step("Check the SSO settings", "Check the storage quota")


def test_short_steps_need_an_exact_match_to_count_as_duplicates():
    assert not is_duplicate_step("Reset it", "Reset the password for the affected user")


def test_merge_drops_restated_playbook_steps_and_keeps_new_ones_after_the_model_steps():
    playbook = (
        "Compare billed seats with active workspace members",
        "Review the last invoices for duplicates",
        "Prepare any refund request for human approval",
        "Confirm the plan's seat price before quoting an amount",
    )
    merged = merge_steps(MODEL_BILLING, playbook)
    assert merged[:3] == MODEL_BILLING
    assert merged[3:] == ["Confirm the plan's seat price before quoting an amount"]


def test_merge_also_removes_duplicates_inside_the_model_steps():
    merged = merge_steps(["Check the token", "1. check the token."], ())
    assert merged == ["Check the token"]


async def test_a_billing_diagnosis_has_no_repeated_steps(tool_env, text_of):
    agent = TroubleshootingAgent(build_read_registry(tool_env))
    d, *_ = await agent.run(text_of("CD-1002"), _cls(Category.billing), [])
    bodies = [re.sub(r"^\d+\.\s*", "", s) for s in d.troubleshooting_steps]
    for i, a in enumerate(bodies):
        for b in bodies[i + 1 :]:
            assert not is_duplicate_step(a, b), (a, b)
