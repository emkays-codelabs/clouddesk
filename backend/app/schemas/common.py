"""Shared domain vocabulary. Defined here first; models and the API import it (CLAUDE.md 5)."""

from enum import StrEnum


class Category(StrEnum):
    login_issue = "login_issue"
    billing = "billing"
    api_failure = "api_failure"
    workspace_permissions = "workspace_permissions"
    storage_quota = "storage_quota"
    integration = "integration"
    feature_request = "feature_request"
    account = "account"
    security = "security"
    other = "other"


class TicketStatus(StrEnum):
    new = "new"
    in_progress = "in_progress"
    waiting_on_customer = "waiting_on_customer"
    waiting_on_approval = "waiting_on_approval"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Channel(StrEnum):
    email = "email"
    chat = "chat"
    web = "web"
    api = "api"


class Role(StrEnum):
    viewer = "viewer"
    agent = "agent"
    admin = "admin"


class MemoryType(StrEnum):
    preference = "preference"
    past_issue = "past_issue"
    troubleshooting = "troubleshooting"
    note = "note"


class ApprovalStatus(StrEnum):
    """Ticket-level approval state; an approval request itself is only pending/approved/rejected."""

    not_required = "not_required"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ResolutionActionStatus(StrEnum):
    planned = "planned"
    pending_approval = "pending_approval"
    approved = "approved"
    executed = "executed"
    rejected = "rejected"
    failed = "failed"


class EscalationStatus(StrEnum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class WorkflowStatus(StrEnum):
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    completed = "completed"
    failed = "failed"
    escalated = "escalated"


class MessageRole(StrEnum):
    customer = "customer"
    agent = "agent"
    system = "system"
    ai = "ai"


class WorkflowEventType(StrEnum):
    node_started = "node_started"
    node_completed = "node_completed"
    tool_called = "tool_called"
    llm_called = "llm_called"
    approval_requested = "approval_requested"
    approval_resolved = "approval_resolved"
    error = "error"
    workflow_completed = "workflow_completed"


class CustomerStatus(StrEnum):
    active = "active"
    trial = "trial"
    past_due = "past_due"
    churned = "churned"


class Plan(StrEnum):
    free = "free"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"
