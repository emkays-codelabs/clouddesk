"""Policy rules (F3, F10, ADR-0003): deterministic, no model, severity only rises."""

import json
from pathlib import Path

import pytest

from agents.rules import (
    ESCALATION_RULES,
    SEVERITY_ORDER,
    matching_escalation_rules,
    rule_category,
    rule_escalation,
    rule_severity,
)
from app.schemas.common import Category, Severity

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data"
TICKETS = {t["ticket_number"]: t for t in json.loads((SAMPLE / "tickets.json").read_text("utf-8"))}
CUSTOMERS = {c["key"]: c for c in json.loads((SAMPLE / "customers.json").read_text("utf-8"))}


def _text(number: str) -> str:
    t = TICKETS[number]
    return f"{t['subject']}\n{t['body']}"


def _plan(number: str) -> str:
    return CUSTOMERS[TICKETS[number]["customer_key"]]["plan_name"]


# ticket -> (category, escalation team or None, minimum severity the rules must give)
EXPECTED = {
    "CD-1001": (Category.login_issue, None, Severity.high),
    "CD-1002": (Category.billing, None, Severity.low),
    "CD-1003": (Category.api_failure, None, Severity.low),
    "CD-1004": (Category.storage_quota, None, Severity.low),
    "CD-1005": (Category.security, "Security team", Severity.critical),
    "CD-1006": (Category.account, "Data protection team", Severity.high),
    "CD-1007": (Category.workspace_permissions, None, Severity.low),
    "CD-1008": (Category.integration, None, Severity.low),
    "CD-1009": (Category.account, "Privacy team", Severity.high),
    "CD-1010": (Category.feature_request, None, Severity.low),
    "CD-1011": (Category.billing, "Billing disputes team", Severity.high),
    "CD-1012": (Category.login_issue, None, Severity.low),
    "CD-1013": (Category.security, None, Severity.high),
}


def test_every_demo_ticket_is_covered():
    assert set(EXPECTED) == set(TICKETS)


@pytest.mark.parametrize("number", sorted(EXPECTED))
def test_demo_ticket_category_escalation_and_severity(number):
    category, team, floor = EXPECTED[number]
    text, plan = _text(number), _plan(number)
    assert rule_category(text) == category
    decision = rule_escalation(text, plan)
    assert decision.required is (team is not None)
    assert decision.team == team
    got = rule_severity(text, plan, model_severity=Severity.low).severity
    assert got == floor


@pytest.mark.parametrize("number", ["CD-1005", "CD-1006", "CD-1009", "CD-1011"])
def test_policy_tickets_escalate_without_a_model(number):
    # Pure functions of text and plan: nothing here can call a model or the database.
    decision = rule_escalation(_text(number), _plan(number))
    assert decision.required and decision.rule_names and decision.team


def test_cd_1010_stays_low_even_when_asked_politely_about_dark_mode():
    assert rule_severity(_text("CD-1010"), "free").severity == Severity.low


def test_severity_is_never_lowered_by_rules():
    text = _text("CD-1010")
    for model in Severity:
        out = rule_severity(text, "free", model_severity=model).severity
        assert SEVERITY_ORDER[out] >= SEVERITY_ORDER[model]
    assert (
        rule_severity(text, "free", model_severity=Severity.critical).severity == Severity.critical
    )


def test_rules_raise_a_lower_model_severity_and_say_why():
    result = rule_severity(_text("CD-1005"), "business", model_severity=Severity.medium)
    assert result.severity == Severity.critical
    assert result.raised and result.reason


def test_rule_table_names_a_team_for_each_policy_area():
    assert {r.name for r in ESCALATION_RULES} == {
        "payment_dispute",
        "account_deletion",
        "security_incident",
        "data_loss",
        "legal",
        "enterprise_outage",
    }
    assert all(r.team for r in ESCALATION_RULES)


def test_legal_matches():
    rules = matching_escalation_rules("Our lawyer says we will sue over a GDPR subpoena", "pro")
    assert [r.name for r in rules] == ["legal"]


def test_enterprise_outage_needs_the_enterprise_plan():
    text = "This is a full outage, the platform is down for all users."
    assert [r.name for r in matching_escalation_rules(text, "enterprise")] == ["enterprise_outage"]
    assert matching_escalation_rules(text, "pro") == []


def test_enterprise_outage_is_case_insensitive_on_plan():
    text = "Complete outage across the company"
    assert matching_escalation_rules(text, "Enterprise")


def test_ordinary_text_matches_nothing():
    assert matching_escalation_rules("How do I change my avatar?", "pro") == []
    assert rule_category("How do I change my avatar?") == Category.other
    assert rule_escalation("hello", "pro").required is False


def test_multiple_rules_list_every_name_and_first_team_wins():
    text = "Unauthorized charge, we are disputing it, and we think our account was breached."
    names = [r.name for r in matching_escalation_rules(text, "pro")]
    assert "payment_dispute" in names and "security_incident" in names
    assert rule_escalation(text, "pro").team == "Security team"  # table order: security first


def test_routine_billing_refund_is_not_a_dispute():
    assert matching_escalation_rules("Please refund 3 unused seats", "business") == []
