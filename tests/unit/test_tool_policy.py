"""ToolPolicy (F9, 7.4): an explicit approval bit per tool; unknown tools need approval."""

import pytest

from app.core.config import Settings
from app.tools.policy import ToolPolicy, validate_provenance


@pytest.mark.parametrize(
    "name",
    [
        "get_customer",
        "get_subscription",
        "get_ticket_history",
        "search_docs",
        "check_service_status",
        "update_ticket",
        "create_escalation",
    ],
)
def test_reads_update_ticket_and_escalation_need_no_approval(name):
    assert ToolPolicy(Settings()).requires_approval(name) is False


def test_reset_demo_setting_needs_approval():
    assert ToolPolicy(Settings()).requires_approval("reset_demo_setting") is True


def test_refund_needs_approval_for_any_amount_by_default():
    policy = ToolPolicy(Settings())
    assert policy.requires_approval("create_refund_request", {"amount": 0.01}) is True
    assert policy.requires_approval("create_refund_request", {"amount": 500}) is True


def test_refund_threshold_applies_only_when_refund_approval_is_off():
    cfg = Settings(approval_required_for_refunds=False, max_refund_without_approval=50)
    policy = ToolPolicy(cfg)
    assert policy.requires_approval("create_refund_request", {"amount": 50}) is False
    assert policy.requires_approval("create_refund_request", {"amount": 50.01}) is True
    assert policy.requires_approval("create_refund_request", {}) is True


def test_refund_approval_flag_wins_over_threshold():
    cfg = Settings(approval_required_for_refunds=True, max_refund_without_approval=1000)
    assert ToolPolicy(cfg).requires_approval("create_refund_request", {"amount": 1}) is True


def test_unknown_tool_always_requires_approval():
    assert ToolPolicy(Settings()).requires_approval("drop_database") is True


def test_risk_tiers_are_low_medium_high_only():
    policy = ToolPolicy(Settings())
    assert policy.risk_tier("create_refund_request") == "high"
    assert policy.risk_tier("update_ticket") == "medium"
    assert policy.risk_tier("get_customer") == "low"
    assert policy.risk_tier("unknown") == "high"


def test_provenance_rejects_amount_not_in_trusted_set():
    assert validate_provenance({"amount": 499.0}, {"cus_1", 120.0}, fields={"amount"}) == ["amount"]


def test_provenance_accepts_amount_from_subscription_record():
    assert validate_provenance({"amount": 120}, {120.0}, fields={"amount"}) == []
    assert validate_provenance({"amount": "120.00"}, {120}, fields={"amount"}) == []


def test_provenance_rejects_id_from_ticket_text_and_ignores_other_fields():
    args = {"customer_id": "cus_evil", "reason": "free text"}
    assert validate_provenance(args, {"cus_1"}, fields={"customer_id"}) == ["customer_id"]
    assert (
        validate_provenance(
            {"customer_id": "cus_1", "reason": "x"}, {"cus_1"}, fields={"customer_id"}
        )
        == []
    )
