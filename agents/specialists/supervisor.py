"""Support Supervisor (F2, F3, F11): classify, assess severity, summarise.

Does: `understand` classifies a ticket into one of the 10 categories with a one-line summary, using
`rule_category` and the model; where a rule matched, the rule's category wins, and the model decides
only when no rule did (ADR-0003). `assess_severity` asks the model, then `rule_severity` can only
raise the result, never lower it. `ticket_summary` writes the closing line deterministically. The
injection scan of the ticket text is carried on the result. A failed model call falls back to the
rules (status "fallback") rather than failing the run.
Must NOT: follow instructions in ticket text (it is wrapped as data), or call a model except
through `call_structured`.
"""

import time
from dataclasses import dataclass, field

from agents.prompts import CLASSIFY_SYSTEM, SEVERITY_SYSTEM, wrap_untrusted
from agents.rules import rule_category, rule_severity
from agents.specialists.common import ToolCallRecord, elapsed_ms
from app.core.injection_guard import InjectionScan, scan_for_injection
from app.core.llm import LLMError, LLMProvider, call_structured
from app.schemas.common import Category, Severity
from app.schemas.workflow import Classification, SeverityAssessment, TokenUsage

RULE_CONFIDENCE = 0.85


@dataclass
class Understanding:
    classification: Classification
    injection: InjectionScan = field(default_factory=lambda: InjectionScan(False, ()))


def _first_line(text: str, limit: int = 140) -> str:
    flat = " ".join(text.split())
    return flat[:limit]


class SupervisorAgent:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    async def understand(
        self, text: str
    ) -> tuple[Understanding, str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        injection = scan_for_injection(text)
        rule = rule_category(text)
        hints = {"category": rule.value} if rule != Category.other else None
        status, usage = "ok", TokenUsage()
        try:
            result = await call_structured(
                Classification,
                system=CLASSIFY_SYSTEM,
                user=wrap_untrusted(text),
                hints=hints,
                tier="fast",
                llm=self._llm,
            )
            usage = result.usage
            classification = result.output
            if rule != Category.other:
                classification = classification.model_copy(
                    update={
                        "category": rule,
                        "confidence": max(classification.confidence, RULE_CONFIDENCE),
                    }
                )
        except LLMError as exc:
            status, usage = "fallback", exc.usage
            classification = Classification(
                category=rule,
                intent=rule.value.replace("_", " "),
                summary=_first_line(text) or "No ticket text supplied.",
                confidence=RULE_CONFIDENCE if rule != Category.other else 0.3,
            )
        return Understanding(classification, injection), status, usage, elapsed_ms(started), []

    async def assess_severity(
        self, text: str, plan_name: str | None = None
    ) -> tuple[SeverityAssessment, str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        status, usage, model = "ok", TokenUsage(), None
        try:
            result = await call_structured(
                SeverityAssessment,
                system=SEVERITY_SYSTEM,
                user=wrap_untrusted(text),
                tier="fast",
                llm=self._llm,
            )
            usage, model = result.usage, result.output
        except LLMError as exc:
            status, usage = "fallback", exc.usage
        verdict = rule_severity(text, plan_name, model.severity if model else None)
        reason = verdict.reason
        if model is not None and verdict.severity == model.severity and not verdict.raised:
            reason = model.reason or reason
        confidence = model.confidence if model is not None else RULE_CONFIDENCE
        assessment = SeverityAssessment(
            severity=Severity(verdict.severity), reason=reason, confidence=confidence
        )
        return assessment, status, usage, elapsed_ms(started), []

    def ticket_summary(
        self,
        ticket_number: str,
        classification: Classification,
        severity: SeverityAssessment,
        outcome: str = "",
    ) -> str:
        """One line for the ticket header and the audit trail; deterministic, no model."""
        line = (
            f"{ticket_number} [{classification.category.value}, {severity.severity.value}]: "
            f"{classification.summary}"
        )
        return f"{line} Outcome: {outcome}" if outcome else line
