"""Workflow types: agent outputs and the run state (06_API_CONTRACT.md, Workflow state).

Does: define every structured output an agent returns (`Classification`, `SeverityAssessment`,
`CustomerContext`, `Diagnosis`, `ResolutionPlan`, `EscalationDecision`) and the full `WorkflowState`
the right-hand panel renders. Every field except the run identity is optional, so a state saved
by an earlier phase, or by a run still in progress, still loads. `extra="allow"` is kept for the
same reason.
Must NOT: hold behaviour. The rules and the model decide; these classes only carry the result.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    ApprovalStatus,
    Category,
    EscalationStatus,
    ResolutionActionStatus,
    Severity,
    WorkflowStatus,
)
from app.schemas.customer import Customer, Subscription, Workspace
from app.schemas.knowledge import Evidence
from app.schemas.ticket import TicketSummary

__all__ = [
    "Classification",
    "CustomerContext",
    "Diagnosis",
    "Escalation",
    "EscalationDecision",
    "Evidence",
    "PlannedAction",
    "PreviousCase",
    "ResolutionAction",
    "ResolutionPlan",
    "RiskAssessment",
    "SeverityAssessment",
    "TokenUsage",
    "WorkflowState",
]


class TokenUsage(BaseModel):
    """Tokens and an estimated cost. The fake provider is always 0.0 (an estimate, never a bill)."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=round(self.estimated_cost_usd + other.estimated_cost_usd, 8),
        )


class Classification(BaseModel):
    category: Category
    intent: str = ""
    summary: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class SeverityAssessment(BaseModel):
    severity: Severity
    reason: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class CustomerContext(BaseModel):
    customer: Customer
    subscription: Subscription | None = None
    workspace: Workspace | None = None
    previous_tickets: list[TicketSummary] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)


class PreviousCase(BaseModel):
    ticket_number: str
    subject: str
    resolution_summary: str
    similarity: float = Field(ge=0, le=1)


class Diagnosis(BaseModel):
    problem: str
    probable_causes: list[str] = Field(default_factory=list)
    troubleshooting_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)


class PlannedAction(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    description: str = ""


class ResolutionPlan(BaseModel):
    summary: str
    customer_response: str
    internal_notes: str = ""
    actions: list[PlannedAction] = Field(default_factory=list)


class EscalationDecision(BaseModel):
    escalation_required: bool
    reason: str = ""
    assigned_team: str = ""
    priority: Severity = Severity.medium
    confidence: float = Field(default=0.5, ge=0, le=1)


class RiskAssessment(BaseModel):
    level: Literal["low", "medium", "high"]
    reasons: list[str] = Field(default_factory=list)


class ResolutionAction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ResolutionActionStatus
    result: dict[str, Any] | None = None
    requires_approval: bool = False
    created_at: datetime
    executed_at: datetime | None = None


class Escalation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    ticket_number: str
    reason: str
    priority: str
    status: EscalationStatus
    created_by: str
    assigned_team: str
    created_at: datetime
    resolved_at: datetime | None = None


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)

    workflow_id: str
    ticket_id: str
    status: WorkflowStatus
    current_node: str | None = None
    completed_nodes: list[str] = Field(default_factory=list)
    classification: Classification | None = None
    severity: Severity | None = None
    severity_reason: str | None = None
    customer_context: CustomerContext | None = None
    retrieved_docs: list[Evidence] = Field(default_factory=list)
    previous_cases: list[PreviousCase] = Field(default_factory=list)
    diagnosis: Diagnosis | None = None
    resolution_plan: ResolutionPlan | None = None
    actions: list[ResolutionAction] = Field(default_factory=list)
    risk: RiskAssessment | None = None
    escalation_required: bool = False
    escalation_reason: str | None = None
    approval_status: ApprovalStatus = ApprovalStatus.not_required
    approval_request_id: str | None = None
    final_response: str | None = None
    ticket_summary: str | None = None
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
