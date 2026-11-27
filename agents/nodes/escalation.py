"""The escalation node (F10): hand the ticket to a named team and record it.

Does: take the decision `risk_check` made (or build one from the reason a run was stopped: a failed
step, an exhausted budget, a rejected approval), record it with `create_escalation` through the
registry and mark the state. Policy rules always win, so a policy decision keeps its own team.
Must NOT: decide anything new with a model, execute an action, or reach a customer.
"""

from typing import Any

from agents.nodes.common import GraphDeps, NodeFn, traced_node
from agents.specialists.common import ToolCallRecord
from agents.specialists.escalation import DEFAULT_TEAM, EscalationAgent
from agents.state import SupportState
from app.core.observability import WorkflowTracer
from app.schemas.common import Severity
from app.schemas.workflow import EscalationDecision

ESCALATION = "escalation"


def _decision(state: SupportState) -> EscalationDecision:
    saved = state.get("escalation")
    reason = state.get("escalation_reason") or "A human team must review this ticket."
    severity = Severity(state.get("severity", Severity.high.value))
    if saved and saved.get("escalation_required"):
        decision = EscalationDecision.model_validate(saved)
        if reason and reason not in decision.reason:
            decision = decision.model_copy(update={"reason": f"{decision.reason} {reason}".strip()})
        return decision
    return EscalationDecision(
        escalation_required=True,
        reason=reason,
        assigned_team=DEFAULT_TEAM,
        priority=severity,
        confidence=1.0,
    )


def escalation(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        decision = _decision(state)
        calls: list[ToolCallRecord] = []
        await EscalationAgent(deps.registry, deps.llm).record(
            state["ticket_id"], decision, state.get("workflow_id", ""), calls
        )
        await tracer.tool_calls(ESCALATION, calls)
        return {
            "escalation_required": True,
            "escalation_reason": decision.reason,
            "escalation": decision.model_dump(mode="json"),
        }

    return traced_node(deps, ESCALATION, body)
