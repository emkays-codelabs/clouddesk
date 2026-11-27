"""Decision nodes (F8, F9, F10, F11): plan, judge the risk, act, remember.

Does: `resolution_planning` drafts the plan (actions come only from the deterministic planner);
`risk_check` scores the risk and decides whether a human team must take the ticket (policy rules
win, then the run budgets, then the model's grey-area judgement); `execute_resolution` runs the
planned actions through `ToolRegistry.execute` (the same path for an automatic run and an
approved one);
`memory_update` writes scrubbed, de-duplicated notes for the customer's next ticket.
Must NOT: run an action that needs approval before a human approved it, invent an action, or
write SQL (the registry and the memory service do).
"""

from datetime import UTC, datetime
from typing import Any

from agents.nodes.common import GraphDeps, NodeFn, traced_node, usage_dict
from agents.rules import matching_escalation_rules
from agents.specialists.common import ToolCallRecord, call_tool, ticket_text
from agents.specialists.escalation import EscalationAgent
from agents.specialists.resolution import ResolutionAgent, reply_failed_validation, trusted_values
from agents.state import ESCALATE_CONFIDENCE, MAX_GRAPH_STEPS, SupportState
from app.core.observability import WorkflowTracer
from app.schemas.common import Severity
from app.schemas.workflow import (
    Classification,
    CustomerContext,
    Diagnosis,
    Evidence,
    ResolutionPlan,
    RiskAssessment,
)
from app.services.customer_memory_service import build_memory_service

PLANNING = "resolution_planning"
RISK = "risk_check"
EXECUTE = "execute_resolution"
MEMORY = "memory_update"


def assess_risk(
    plan: ResolutionPlan | None,
    severity: Severity,
    injection_flags: list[str],
    policy_escalation: bool,
) -> RiskAssessment:
    """High when the plan needs approval, a policy case fired, severity is critical, injection
    was detected or the reply failed validation (CLAUDE.md 7.3)."""
    reasons: list[str] = []
    if plan is not None and any(a.requires_approval for a in plan.actions):
        reasons.append("The plan has an action that needs a human approval.")
    if policy_escalation:
        reasons.append("A policy rule requires a human team.")
    if severity == Severity.critical:
        reasons.append("Severity is critical.")
    if injection_flags:
        reasons.append("The ticket text looks like a prompt-injection attempt.")
    if plan is not None and reply_failed_validation(plan):
        reasons.append("The drafted reply failed output validation.")
    if reasons:
        return RiskAssessment(level="high", reasons=reasons)
    if severity == Severity.high:
        return RiskAssessment(level="medium", reasons=["Severity is high."])
    return RiskAssessment(level="low", reasons=[])


def pending_approval_actions(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [a for a in (plan or {}).get("actions", []) if a.get("requires_approval")]


def resolution_planning(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        agent = ResolutionAgent(deps.ctx.settings, deps.llm)
        plan, _status, usage, ms, calls = await agent.run(
            state["ticket_id"],
            ticket_text(state.get("subject", ""), state.get("body", "")),
            Classification.model_validate(state["classification"]),
            CustomerContext.model_validate(state["customer_context"]),
            [Evidence.model_validate(e) for e in state.get("retrieved_docs", [])],
            Diagnosis.model_validate(state["diagnosis"]),
        )
        await tracer.tool_calls(PLANNING, calls)
        await tracer.llm(PLANNING, usage_dict(usage), ms, "resolution plan")
        return {
            "resolution_plan": plan.model_dump(mode="json"),
            "final_response": plan.customer_response,
            "token_usage": usage_dict(usage),
        }

    return traced_node(deps, PLANNING, body)


def risk_check(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        text = ticket_text(state.get("subject", ""), state.get("body", ""))
        classification = Classification.model_validate(state["classification"])
        diagnosis = Diagnosis.model_validate(state["diagnosis"])
        severity = Severity(state.get("severity", Severity.medium.value))
        plan = ResolutionPlan.model_validate(state["resolution_plan"])
        policy = bool(matching_escalation_rules(text, state.get("plan_name")))

        decision, _status, usage = await EscalationAgent(deps.registry, deps.llm).decide(
            text, state.get("plan_name"), classification, severity
        )
        reasons: list[str] = []
        if decision.escalation_required:
            reasons.append(decision.reason)
        if state.get("injection_flags"):
            reasons.append(
                "The ticket text looks like a prompt-injection attempt; a person must review it."
            )
        if state.get("step_count", 0) >= MAX_GRAPH_STEPS:
            reasons.append("The run used its step budget.")
        if min(classification.confidence, diagnosis.confidence) < ESCALATE_CONFIDENCE:
            reasons.append("Confidence is below the escalation threshold.")

        risk = assess_risk(plan, severity, state.get("injection_flags", []), policy)
        await tracer.llm(RISK, usage_dict(usage), 0, "escalation judgement")
        update: dict[str, Any] = {
            "risk": risk.model_dump(mode="json"),
            "escalation": decision.model_dump(mode="json"),
            "token_usage": usage_dict(usage),
        }
        if reasons:
            update["escalation_required"] = True
            update["escalation_reason"] = " ".join(r for r in reasons if r)
        return update

    return traced_node(deps, RISK, body)


def execute_resolution(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        plan = ResolutionPlan.model_validate(state["resolution_plan"])
        context = CustomerContext.model_validate(state["customer_context"])
        approved = state.get("approval_status") == "approved"
        trusted = trusted_values(context)
        calls: list[ToolCallRecord] = []
        results: list[dict[str, Any]] = []
        now = datetime.now(UTC).isoformat()
        for index, action in enumerate(plan.actions):
            row: dict[str, Any] = {
                "id": f"{state['workflow_id']}:{index}",
                "ticket_id": state["ticket_id"],
                "tool": action.tool,
                "arguments": action.arguments,
                "requires_approval": action.requires_approval,
                "created_at": now,
                "result": None,
            }
            if action.requires_approval and not approved:
                results.append({**row, "status": "rejected"})
                continue
            record = await call_tool(
                deps.registry,
                calls,
                action.tool,
                action.arguments,
                approved=approved and action.requires_approval,
                ticket_id=state["ticket_id"],
                workflow_id=state["workflow_id"],
                trusted_values=trusted,
            )
            result = record.data if isinstance(record.data, dict) else {"error": record.error}
            results.append(
                {
                    **row,
                    "status": "executed" if record.ok else "failed",
                    "result": result,
                    "executed_at": now if record.ok else None,
                }
            )
        await tracer.tool_calls(EXECUTE, calls)
        return {"actions": results}

    return traced_node(deps, EXECUTE, body)


def memory_update(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        classification = state.get("classification") or {}
        diagnosis = state.get("diagnosis") or {}
        plan = state.get("resolution_plan") or {}
        async with deps.ctx.session_factory() as session:
            report = await build_memory_service(session).record_resolution(
                customer_id=state["customer_id"],
                ticket_id=state["ticket_id"],
                category=classification.get("category", "other"),
                summary=classification.get("summary", state.get("subject", "")),
                steps=diagnosis.get("troubleshooting_steps", []),
                resolution=plan.get("summary", state.get("ticket_summary", "")),
                ticket_body=state.get("body"),
            )
            await session.commit()
        return {"memory_written": len(report.written)}

    return traced_node(deps, MEMORY, body)
