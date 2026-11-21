"""Dashboard summary (docs/design/06_API_CONTRACT.md, Dashboard)."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ticket import TicketSummary


class DashboardSummary(BaseModel):
    open_tickets: int
    resolved_today: int
    pending_approvals: int
    escalations_open: int
    avg_resolution_minutes: float
    by_severity: dict[str, int]
    by_category: dict[str, int]
    recent_tickets: list[TicketSummary]
    # Workflow events arrive with the graph (Phase 10); an empty list until then.
    agent_activity: list[dict[str, Any]] = Field(default_factory=list)
