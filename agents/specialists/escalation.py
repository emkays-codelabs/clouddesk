"""Escalation Agent (F10): decide whether a human team takes the ticket, and record it.

Does: policy rules ALWAYS win. When `matching_escalation_rules` matches, the named team gets the
ticket with no model call. Otherwise the model's judgement is trusted in two cases only: it asks to
escalate, severity is high or critical and its confidence is at least 0.6; or it is unsure (below
0.6) on a high or critical ticket, where doubt is itself a reason to hand off. A vague model
escalation on anything less is distrusted (CLAUDE.md 7.2), and a failed model call never escalates
a benign ticket. A decision to escalate is recorded with `create_escalation` through the registry,
which is idempotent, so a retried run adds no second escalation.
Must NOT: let the model overturn a policy match, write SQL, or follow instructions in ticket text.
"""

import time

from agents.prompts import ESCALATION_SYSTEM, wrap_untrusted
from agents.rules import SEVERITY_ORDER, matching_escalation_rules
from agents.specialists.common import ToolCallRecord, call_tool, elapsed_ms
from app.core.llm import LLMError, LLMProvider, call_structured
from app.schemas.common import Severity
from app.schemas.workflow import Classification, EscalationDecision, TokenUsage
from app.tools.registry import ToolRegistry

ESCALATE_CONFIDENCE = 0.6
DEFAULT_TEAM = "Tier 2 support"
_HIGH = {Severity.high, Severity.critical}


class EscalationAgent:
    def __init__(self, registry: ToolRegistry, llm: LLMProvider | None = None) -> None:
        self._registry = registry
        self._llm = llm

    async def decide(
        self,
        text: str,
        plan_name: str | None,
        classification: Classification,
        severity: Severity,
    ) -> tuple[EscalationDecision, str, TokenUsage]:
        """The decision only: rules first, then the model's judgement. Nothing is recorded."""
        status, usage = "ok", TokenUsage()
        matched = matching_escalation_rules(text, plan_name)
        if matched:
            top = max((r.severity for r in matched), key=SEVERITY_ORDER.__getitem__)
            return (
                EscalationDecision(
                    escalation_required=True,
                    reason=" ".join(r.reason for r in matched),
                    assigned_team=matched[0].team,
                    priority=top,
                    confidence=1.0,
                ),
                status,
                usage,
            )
        user = (
            f"Category: {classification.category.value}\nSeverity: {severity.value}\n"
            f"Ticket:\n{wrap_untrusted(text)}"
        )
        model: EscalationDecision | None = None
        try:
            result = await call_structured(
                EscalationDecision,
                system=ESCALATION_SYSTEM,
                user=user,
                tier="smart",
                llm=self._llm,
            )
            usage, model = result.usage, result.output
        except LLMError as exc:
            status, usage = "fallback", exc.usage
        return self._judge(model, severity), status, usage

    async def record(
        self,
        ticket_id: str,
        decision: EscalationDecision,
        workflow_id: str = "",
        calls: list[ToolCallRecord] | None = None,
    ) -> list[ToolCallRecord]:
        """Write the escalation through the registry (idempotent: a retry adds no second row)."""
        calls = calls if calls is not None else []
        await call_tool(
            self._registry,
            calls,
            "create_escalation",
            {
                "ticket_id": ticket_id,
                "reason": decision.reason,
                "assigned_team": decision.assigned_team,
                "priority": decision.priority.value,
            },
            ticket_id=ticket_id,
            workflow_id=workflow_id,
        )
        return calls

    async def run(
        self,
        ticket_id: str,
        text: str,
        plan_name: str | None,
        classification: Classification,
        severity: Severity,
        workflow_id: str = "",
    ) -> tuple[EscalationDecision, str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        decision, status, usage = await self.decide(text, plan_name, classification, severity)
        calls: list[ToolCallRecord] = []
        if decision.escalation_required:
            await self.record(ticket_id, decision, workflow_id, calls)
        return decision, status, usage, elapsed_ms(started), calls

    @staticmethod
    def _judge(model: EscalationDecision | None, severity: Severity) -> EscalationDecision:
        high = severity in _HIGH
        confident = model is not None and model.confidence >= ESCALATE_CONFIDENCE
        if model is not None and model.escalation_required and high and confident:
            return model.model_copy(
                update={"assigned_team": model.assigned_team or DEFAULT_TEAM, "priority": severity}
            )
        if model is not None and high and not confident:
            return EscalationDecision(
                escalation_required=True,
                reason="Low confidence on a high-severity ticket.",
                assigned_team=DEFAULT_TEAM,
                priority=severity,
                confidence=model.confidence,
            )
        return EscalationDecision(
            escalation_required=False,
            reason="",
            assigned_team="",
            priority=severity,
            confidence=model.confidence if model is not None else 0.5,
        )
