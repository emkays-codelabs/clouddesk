"""Supervisor nodes (F2, F3, F11): understand the ticket, assess severity, write the summary.

Does: `understand_ticket` classifies the ticket (rules win, the model fills the gaps), scans the
text for injection and keeps the flags; `classify_severity` asks for a severity that rules may only
raise; `ticket_summary` closes the run with a deterministic one-line summary.
Must NOT: call a model except through the Supervisor agent, or follow instructions in ticket text.
"""

from typing import Any

from agents.nodes.common import GraphDeps, NodeFn, traced_node, usage_dict
from agents.specialists.common import ticket_text
from agents.specialists.supervisor import SupervisorAgent
from agents.state import SupportState
from app.core.observability import WorkflowTracer
from app.schemas.common import Severity
from app.schemas.workflow import Classification, SeverityAssessment

UNDERSTAND = "understand_ticket"
CLASSIFY = "classify_severity"
SUMMARY = "ticket_summary"


def understand_ticket(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        text = ticket_text(state.get("subject", ""), state.get("body", ""))
        understanding, _status, usage, ms, calls = await SupervisorAgent(deps.llm).understand(text)
        await tracer.tool_calls(UNDERSTAND, calls)
        await tracer.llm(UNDERSTAND, usage_dict(usage), ms, "classification")
        return {
            "classification": understanding.classification.model_dump(mode="json"),
            "injection_flags": list(understanding.injection.flags),
            "token_usage": usage_dict(usage),
        }

    return traced_node(deps, UNDERSTAND, body)


def classify_severity(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        text = ticket_text(state.get("subject", ""), state.get("body", ""))
        assessment, _status, usage, ms, calls = await SupervisorAgent(deps.llm).assess_severity(
            text, state.get("plan_name")
        )
        await tracer.tool_calls(CLASSIFY, calls)
        await tracer.llm(CLASSIFY, usage_dict(usage), ms, "severity")
        return {
            "severity": assessment.severity.value,
            "severity_reason": assessment.reason,
            "severity_confidence": assessment.confidence,
            "token_usage": usage_dict(usage),
        }

    return traced_node(deps, CLASSIFY, body)


def ticket_summary(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        # A run stopped early (a failed step) may have no classification: summarise what exists.
        classification = Classification.model_validate(
            state.get("classification")
            or {"category": "other", "summary": state.get("subject", "")[:140]}
        )
        severity = SeverityAssessment(
            severity=Severity(state.get("severity", Severity.medium.value)),
            reason=state.get("severity_reason", ""),
        )
        if state.get("escalation_required"):
            outcome = f"escalated: {state.get('escalation_reason', '')}".strip()
        elif state.get("approval_status") == "approved":
            outcome = "approved actions executed"
        else:
            outcome = "reply drafted for the agent to send"
        line = SupervisorAgent(deps.llm).ticket_summary(
            state.get("ticket_number", ""), classification, severity, outcome
        )
        return {"ticket_summary": line}

    return traced_node(deps, SUMMARY, body)
