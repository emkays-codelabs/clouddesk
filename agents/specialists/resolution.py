"""Resolution Agent (F8): summary, grounded customer reply, internal notes and planned actions.

Does: `plan_actions` is the only source of actions and is deterministic: a seat refund (amount and
ids computed from the customer's subscription and workspace, never from ticket text), a workspace
setting reset only when the ticket asks for one, and a status update. Every action carries
`requires_approval` from `ToolPolicy`; a policy escalation plans nothing, the Escalation agent owns
it. `run` asks the model for the wording only, then `_ground_response` keeps the draft sentences
the evidence supports and appends the diagnosis steps and the cited article titles. The reply goes
through `validate_customer_output`: a groundedness miss is revised once (steps and citation only),
and a second miss or any leak withholds the reply and marks the plan with
`VALIDATION_FAILED_MARKER` so the risk check escalates. Nothing is executed here.
Must NOT: let the model add or change an action, put ticket text in tool arguments, or call a tool.
"""

import re
import time
from typing import Any

from agents.prompts import RESOLUTION_SYSTEM, wrap_untrusted
from agents.rules import matching_escalation_rules
from agents.specialists.common import ToolCallRecord, elapsed_ms
from app.core.config import Settings
from app.core.llm import LLMError, LLMProvider, call_structured
from app.core.output_validation import (
    groundedness,
    next_step,
    validate_customer_output,
)
from app.schemas.common import Category
from app.schemas.workflow import (
    Classification,
    CustomerContext,
    Diagnosis,
    Evidence,
    PlannedAction,
    ResolutionPlan,
    TokenUsage,
)
from app.tools.policy import ToolPolicy, validate_provenance

VALIDATION_FAILED_MARKER = "OUTPUT_VALIDATION_FAILED"
HOLDING_REPLY = (
    "Thank you for contacting CloudDesk. A support specialist will review your request and "
    "reply to you shortly."
)
MAX_CITED_ARTICLES = 2
REFUND_REASON = "Seats billed exceed active workspace members."

_REFUND_ASK = re.compile(r"\brefund|\bcredit back|money back", re.IGNORECASE)
_RESET_ASK = re.compile(
    r"\breset\s+(?:the\s+|our\s+|my\s+)?(sso|mfa|sharing|integrations?)\s+(?:setting|config)",
    re.IGNORECASE,
)
_NUMBERING = re.compile(r"^\s*(\d+[.)]|[-*])\s*")
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def refund_amount(context: CustomerContext) -> float | None:
    """Unused seats times the per-seat price, from the subscription and workspace only."""
    sub, workspace = context.subscription, context.workspace
    if sub is None or workspace is None or sub.seats <= 0:
        return None
    unused = sub.seats - workspace.member_count
    if unused <= 0:
        return None
    return round(unused * sub.mrr / sub.seats, 2)


def trusted_values(context: CustomerContext) -> set[Any]:
    """Ids and amounts a tool argument may carry: customer context only, never ticket text."""
    values: set[Any] = {context.customer.id}
    if context.subscription is not None:
        values.add(context.subscription.id)
    if context.workspace is not None:
        values.add(context.workspace.id)
    amount = refund_amount(context)
    if amount is not None:
        values.add(amount)
    return values


def reply_failed_validation(plan: ResolutionPlan) -> bool:
    return VALIDATION_FAILED_MARKER in plan.internal_notes


def _plain(step: str) -> str:
    return _NUMBERING.sub("", step).strip()


def _steps_block(diagnosis: Diagnosis) -> str:
    steps = [_plain(s) for s in diagnosis.troubleshooting_steps if _plain(s)]
    return "\n".join(f"{n}. {s}" for n, s in enumerate(steps, 1))


def _cited_chunks(evidence: list[Evidence], diagnosis: Diagnosis) -> list[Any]:
    return [*evidence, *[_plain(s) for s in diagnosis.troubleshooting_steps]]


def _ground_response(
    draft: str, evidence: list[Evidence], diagnosis: Diagnosis, first_name: str = ""
) -> str:
    """Keep the draft sentences the evidence supports, then add the steps and the source titles."""
    chunks = _cited_chunks(evidence, diagnosis)
    kept = [
        s.strip()
        for s in _SENTENCE.split(draft or "")
        if s.strip() and groundedness(s, chunks) >= 1.0
    ]
    parts = [f"Hello {first_name}," if first_name else "Hello,"]
    parts += kept
    steps = _steps_block(diagnosis)
    if steps:
        parts.append(f"Here are the steps we suggest:\n{steps}")
    titles = list(dict.fromkeys(e.title for e in evidence))[:MAX_CITED_ARTICLES]
    if titles:
        parts.append("Source: " + "; ".join(titles) + ".")
    return "\n".join(parts)


class ResolutionAgent:
    def __init__(self, settings: Settings, llm: LLMProvider | None = None) -> None:
        self._policy = ToolPolicy(settings)
        self._llm = llm

    def plan_actions(
        self, ticket_id: str, text: str, category: Category, context: CustomerContext
    ) -> list[PlannedAction]:
        """The deterministic action plan. The model has no say in it."""
        if matching_escalation_rules(text, context.customer.plan_name):
            return []
        planned: list[tuple[str, dict[str, Any], str]] = []
        amount = refund_amount(context)
        if category == Category.billing and _REFUND_ASK.search(text) and amount is not None:
            planned.append(
                (
                    "create_refund_request",
                    {
                        "customer_id": context.customer.id,
                        "subscription_id": context.subscription.id,
                        "amount": amount,
                        "reason": REFUND_REASON,
                    },
                    f"Refund INR {amount:,.2f} for unused seats",
                )
            )
        reset = _RESET_ASK.search(text)
        if reset and context.workspace is not None:
            setting = reset.group(1).lower()
            planned.append(
                (
                    "reset_demo_setting",
                    {"workspace_id": context.workspace.id, "setting": setting},
                    f"Reset the {setting} setting",
                )
            )
        trusted = trusted_values(context)
        actions: list[PlannedAction] = []
        for tool, args, description in planned:
            fields = self._policy.provenance_fields(tool)
            if validate_provenance(args, trusted, fields):
                continue  # an argument without provenance is dropped, never executed
            actions.append(
                PlannedAction(
                    tool=tool,
                    arguments=args,
                    requires_approval=self._policy.requires_approval(tool, args),
                    description=description,
                )
            )
        waiting = any(a.requires_approval for a in actions)
        status = "waiting_on_approval" if waiting else "resolved"
        args = {"ticket_id": ticket_id, "status": status}
        actions.append(
            PlannedAction(
                tool="update_ticket",
                arguments=args,
                requires_approval=self._policy.requires_approval("update_ticket", args),
                description=f"Set the ticket status to {status}",
            )
        )
        return actions

    async def run(
        self,
        ticket_id: str,
        text: str,
        classification: Classification,
        context: CustomerContext,
        evidence: list[Evidence],
        diagnosis: Diagnosis,
    ) -> tuple[ResolutionPlan, str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        actions = self.plan_actions(ticket_id, text, classification.category, context)
        evidence_text = "\n".join(f"[{e.title}] {e.snippet}" for e in evidence) or "none"
        user = (
            f"Category: {classification.category.value}\n"
            f"Ticket:\n{wrap_untrusted(text)}\n"
            f"Knowledge-base evidence:\n{wrap_untrusted(evidence_text)}\n"
            f"Diagnosis steps:\n{wrap_untrusted(_steps_block(diagnosis))}"
        )
        status, usage, summary, draft, notes = "ok", TokenUsage(), "", "", ""
        try:
            result = await call_structured(
                ResolutionPlan,
                system=RESOLUTION_SYSTEM,
                user=user,
                hints={"summary": f"Resolve: {classification.summary}"},
                tier="smart",
                llm=self._llm,
            )
            usage = result.usage
            summary = result.output.summary
            draft, notes = result.output.customer_response, result.output.internal_notes
        except LLMError as exc:
            status, usage = "fallback", exc.usage
        summary = summary or f"Resolve: {classification.summary}"

        first_name = (context.customer.name.split() or [""])[0]
        chunks = _cited_chunks(evidence, diagnosis)
        reply = _ground_response(draft, evidence, diagnosis, first_name)
        verdict = validate_customer_output(reply, chunks)
        step = next_step(verdict, 0)
        if step == "revise":
            reply = _ground_response("", evidence, diagnosis, first_name)
            verdict = validate_customer_output(reply, chunks)
            step = next_step(verdict, 1)
        failed = step != "send"
        if failed:
            reply = HOLDING_REPLY
            notes = f"{notes}\n{VALIDATION_FAILED_MARKER}: {', '.join(verdict.reasons)}".strip()
        for action in actions:
            if action.tool == "create_refund_request":
                notes = f"{notes}\n{action.description}; needs human approval.".strip()
        plan = ResolutionPlan(
            summary=summary, customer_response=reply, internal_notes=notes, actions=actions
        )
        return plan, status, usage, elapsed_ms(started), []
