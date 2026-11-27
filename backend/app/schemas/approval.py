"""Approval, event and agent-overview types (docs/design/06_API_CONTRACT.md).

Does: carry the shapes of `GET /approvals`, the approve and reject bodies and replies,
`GET /tickets/{id}/events` and `GET /agents`.
Must NOT: hold behaviour; the services build these from rows.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ApprovalStatus, EscalationStatus, WorkflowEventType
from app.schemas.workflow import PlannedAction, WorkflowState


class ApprovalRequest(BaseModel):
    id: str
    ticket_id: str
    ticket_number: str
    workflow_id: str
    action: PlannedAction
    risk_level: str
    reason: str
    requested_by: str
    status: ApprovalStatus
    decided_by: str | None = None
    decision_note: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


class ApprovalDecisionBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ApprovalDecisionResult(BaseModel):
    approval: ApprovalRequest
    workflow: WorkflowState | None = None


class EscalationUpdate(BaseModel):
    status: EscalationStatus
    note: str | None = Field(default=None, max_length=1000)


class WorkflowEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    ticket_id: str
    event_type: WorkflowEventType
    node: str | None = None
    tool: str | None = None
    message: str = ""
    duration_ms: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentInfo(BaseModel):
    name: str
    role: str
    description: str
    tools: list[str] = Field(default_factory=list)
    last_run_at: datetime | None = None
    runs: int = 0
    avg_duration_ms: float = 0.0


class GraphNode(BaseModel):
    id: str
    label: str


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str | None = None


class AgentGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AgentStats(BaseModel):
    runs_total: int = 0
    runs_completed: int = 0
    runs_failed: int = 0
    avg_duration_ms: float = 0.0
    total_tokens: int = 0
    total_estimated_cost_usd: float = 0.0


class AgentsOverview(BaseModel):
    agents: list[AgentInfo]
    graph: AgentGraph
    recent_runs: list[WorkflowState]
    stats: AgentStats
