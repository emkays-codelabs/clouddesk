"""P10-1, P10-4, P10-5 (F11, F13): state reducers, the checkpointer choice, risk and graph shape."""

import operator

import pytest

from agents.checkpointer import checkpointer_kind, open_checkpointer
from agents.graph import (
    APPROVAL,
    ESCALATION,
    EXECUTE,
    GRAPH_EDGES,
    GRAPH_NODES,
    route_after_approval,
    route_after_risk,
)
from agents.nodes.decision import assess_risk, pending_approval_actions
from agents.specialists.resolution import VALIDATION_FAILED_MARKER
from agents.state import ESCALATE_CONFIDENCE, MAX_GRAPH_STEPS, SupportState, merge_usage
from app.schemas.common import Severity
from app.schemas.workflow import PlannedAction, ResolutionPlan


def test_the_budgets_match_the_spec():
    assert MAX_GRAPH_STEPS == 12
    assert ESCALATE_CONFIDENCE == 0.6


def test_usage_is_summed_not_overwritten():
    first = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    second = {
        "prompt_tokens": 1,
        "completion_tokens": 2,
        "total_tokens": 3,
        "estimated_cost_usd": 0.5,
    }

    merged = merge_usage(first, second)

    assert merged["total_tokens"] == 18
    assert merged["estimated_cost_usd"] == 0.5
    assert merge_usage(None, None)["total_tokens"] == 0


def test_the_progress_fields_append_and_never_overwrite():
    hints = SupportState.__annotations__
    for name in ("errors", "completed_nodes", "route_history"):
        assert hints[name].__metadata__ == (operator.add,)
    assert hints["step_count"].__metadata__ == (operator.add,)
    assert hints["token_usage"].__metadata__ == (merge_usage,)


def test_the_state_carries_no_tenant_field():
    # The tenant filter lives only in repositories (CLAUDE.md 6).
    assert "tenant_id" not in SupportState.__annotations__


def test_the_checkpointer_follows_the_path():
    assert checkpointer_kind(":memory:") == "memory"
    assert checkpointer_kind("") == "memory"
    assert checkpointer_kind("./data/checkpoints.db") == "sqlite"


async def test_a_file_checkpointer_opens_and_closes(tmp_path):
    path = tmp_path / "nested" / "cp.db"

    async with open_checkpointer(str(path)) as saver:
        assert saver is not None

    assert path.exists()


def _plan(*, approval: bool, failed_validation: bool = False) -> ResolutionPlan:
    actions = (
        [PlannedAction(tool="create_refund_request", requires_approval=True)] if approval else []
    )
    notes = VALIDATION_FAILED_MARKER if failed_validation else ""
    return ResolutionPlan(summary="s", customer_response="r", internal_notes=notes, actions=actions)


@pytest.mark.parametrize(
    ("plan", "severity", "flags", "policy"),
    [
        (_plan(approval=True), Severity.low, [], False),
        (_plan(approval=False), Severity.critical, [], False),
        (_plan(approval=False), Severity.low, ["ignore_instructions"], False),
        (_plan(approval=False), Severity.low, [], True),
        (_plan(approval=False, failed_validation=True), Severity.low, [], False),
    ],
    ids=["approval-needed", "critical", "injection", "policy", "validation-failed"],
)
def test_risk_is_high_for_each_listed_cause(plan, severity, flags, policy):
    assert assess_risk(plan, severity, flags, policy).level == "high"


def test_risk_is_low_for_an_ordinary_ticket_and_medium_for_high_severity():
    assert assess_risk(_plan(approval=False), Severity.low, [], False).level == "low"
    assert assess_risk(_plan(approval=False), Severity.high, [], False).level == "medium"


def test_the_graph_has_twelve_steps_and_every_edge_points_at_one():
    ids = {n["id"] for n in GRAPH_NODES}

    assert len(GRAPH_NODES) == 12
    assert all(e["source"] in ids and e["target"] in ids for e in GRAPH_EDGES)


def test_routing_after_the_risk_check():
    refund = {"actions": [{"requires_approval": True}]}
    assert route_after_risk({"escalation_required": True}) == ESCALATION
    assert route_after_risk({"failed": True}) == ESCALATION
    assert route_after_risk({"resolution_plan": refund}) == APPROVAL
    assert route_after_risk({"resolution_plan": {"actions": []}}) == EXECUTE
    assert pending_approval_actions(refund)


def test_routing_after_the_approval():
    assert route_after_approval({"approval_status": "approved"}) == EXECUTE
    assert route_after_approval({"approval_status": "rejected"}) == ESCALATION
    assert route_after_approval({}) == ESCALATION  # no decision is never an approval
