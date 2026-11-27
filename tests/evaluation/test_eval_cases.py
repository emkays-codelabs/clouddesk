"""P9-8: the evaluation dataset loads and every case is well formed (CLAUDE.md 13)."""

import json
from pathlib import Path

import pytest

from agents.rules import matching_escalation_rules, rule_category
from app.schemas.common import Category

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "datasets" / "eval_cases.json").read_text("utf-8"))
TICKETS = {
    t["ticket_number"]: t
    for t in json.loads((ROOT / "sample_data" / "tickets.json").read_text("utf-8"))
}
SLUGS = {p.stem for p in (ROOT / "sample_data" / "knowledge_base").glob("*.md")}
TOOLS = {"update_ticket", "create_refund_request", "reset_demo_setting", "create_escalation"}


def _text(case):
    if "ticket" in case:
        t = TICKETS[case["ticket"]]
        return f"{t['subject']}\n{t['body']}"
    return case["text"]


def test_the_file_loads_and_ids_are_unique():
    assert isinstance(CASES, list) and len(CASES) >= 13
    assert len({c["id"] for c in CASES}) == len(CASES)


def test_every_demo_ticket_has_a_case():
    assert {c["ticket"] for c in CASES if "ticket" in c} == set(TICKETS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_each_case_is_well_formed(case):
    assert ("ticket" in case) != ("text" in case), "exactly one of ticket or text"
    if "ticket" in case:
        assert case["ticket"] in TICKETS
    assert case["expected_category"] in {c.value for c in Category}
    assert isinstance(case["expected_escalation"], bool)
    assert case["expected_article"] in SLUGS
    assert set(case["expected_actions"]) <= TOOLS


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_labels_agree_with_the_policy_rules(case):
    text = _text(case)
    matched = matching_escalation_rules(text, case.get("plan_name"))
    assert bool(matched) == case["expected_escalation"]
    if matched and "expected_team" in case:
        assert matched[0].team == case["expected_team"]
    assert rule_category(text).value == case["expected_category"]
