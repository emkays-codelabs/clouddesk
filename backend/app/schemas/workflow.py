"""Workflow-adjacent response types the ticket contract embeds (06_API_CONTRACT.md, Workflow state).

Only what TicketDetail needs now. WorkflowState is a minimal forward-compatible shape: the fields
every run has, with extra keys kept so the agent phases can add the rest without breaking readers.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EscalationStatus, ResolutionActionStatus, WorkflowStatus


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)

    workflow_id: str
    ticket_id: str
    status: WorkflowStatus
    current_node: str | None = None
    completed_nodes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None


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
