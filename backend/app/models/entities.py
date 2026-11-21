"""Portable SQLAlchemy 2 models: JSON not JSONB, String(36) UUIDs, VARCHAR+CHECK enums.

The same code runs on SQLite (demo) and Postgres (cloud). Every data table carries a not-null,
indexed tenant_id that leads every composite index (D1, ADR-0001).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas.common import (
    ApprovalStatus,
    Category,
    Channel,
    EscalationStatus,
    MemoryType,
    MessageRole,
    ResolutionActionStatus,
    Role,
    Severity,
    TicketStatus,
    WorkflowEventType,
    WorkflowStatus,
)

# Fixed and a valid UUID: the RLS policies cast with ::uuid, and the seed reuses this id.
DEMO_TENANT_ID = "00000000-0000-4000-8000-000000000001"


def new_id() -> str:
    return str(uuid.uuid4())


def enum_col(enum: type[StrEnum]) -> sa.Enum:
    # VARCHAR + CHECK on both databases; no Postgres CREATE TYPE.
    return sa.Enum(
        enum,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda e: [m.value for m in e],
        length=32,
    )


def _dt() -> sa.DateTime:
    return sa.DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(_dt(), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(
        _dt(), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class TenantMixin:
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False, index=True
    )


def _pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=new_id)


def _fk(table: str) -> Mapped[str]:
    return mapped_column(String(36), ForeignKey(f"{table}.id"))


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"
    id: Mapped[str] = _pk()
    name: Mapped[str] = mapped_column(String(200))


class Profile(TenantMixin, TimestampMixin, Base):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)
    id: Mapped[str] = _pk()
    email: Mapped[str] = mapped_column(String(320))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(enum_col(Role), default=Role.viewer)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Customer(TenantMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)
    id: Mapped[str] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    company: Mapped[str] = mapped_column(String(200), default="")
    plan_name: Mapped[str] = mapped_column(String(50), default="free")
    status: Mapped[str] = mapped_column(String(32), default="active")
    region: Mapped[str] = mapped_column(String(50), default="")
    lifetime_value: Mapped[float] = mapped_column(sa.Float, default=0.0)


class Subscription(TenantMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_tenant_customer", "tenant_id", "customer_id"),)
    id: Mapped[str] = _pk()
    customer_id: Mapped[str] = _fk("customers")
    plan: Mapped[str] = mapped_column(String(50))
    seats: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(32), default="active")
    renews_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)
    mrr: Mapped[float] = mapped_column(sa.Float, default=0.0)
    storage_quota_gb: Mapped[float] = mapped_column(sa.Float, default=0.0)
    storage_used_gb: Mapped[float] = mapped_column(sa.Float, default=0.0)
    api_rate_limit: Mapped[int] = mapped_column(default=0)


class Workspace(TenantMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (Index("ix_workspaces_tenant_customer", "tenant_id", "customer_id"),)
    id: Mapped[str] = _pk()
    customer_id: Mapped[str] = _fk("customers")
    name: Mapped[str] = mapped_column(String(200))
    member_count: Mapped[int] = mapped_column(default=0)
    storage_used_gb: Mapped[float] = mapped_column(sa.Float, default=0.0)
    integrations: Mapped[list[Any]] = mapped_column(sa.JSON, default=list)
    sso_enabled: Mapped[bool] = mapped_column(default=False)


class Product(TenantMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "slug"),)
    id: Mapped[str] = _pk()
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    features: Mapped[list[Any]] = mapped_column(sa.JSON, default=list)


class Ticket(TenantMixin, TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ticket_number"),
        Index("ix_tickets_tenant_status_severity", "tenant_id", "status", "severity"),
        Index("ix_tickets_tenant_customer_created", "tenant_id", "customer_id", "created_at"),
    )
    id: Mapped[str] = _pk()
    ticket_number: Mapped[str] = mapped_column(String(32))
    customer_id: Mapped[str] = _fk("customers")
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(enum_col(TicketStatus), default=TicketStatus.new)
    severity: Mapped[Severity | None] = mapped_column(enum_col(Severity), nullable=True)
    category: Mapped[Category | None] = mapped_column(enum_col(Category), nullable=True)
    channel: Mapped[Channel] = mapped_column(enum_col(Channel), default=Channel.web)
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tags: Mapped[list[Any]] = mapped_column(sa.JSON, default=list)
    escalation_required: Mapped[bool] = mapped_column(default=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_col(ApprovalStatus), default=ApprovalStatus.not_required
    )
    resolved_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)


class TicketMessage(TenantMixin, TimestampMixin, Base):
    __tablename__ = "ticket_messages"
    __table_args__ = (
        Index("ix_ticket_messages_tenant_ticket_created", "tenant_id", "ticket_id", "created_at"),
    )
    id: Mapped[str] = _pk()
    ticket_id: Mapped[str] = _fk("tickets")
    role: Mapped[MessageRole] = mapped_column(enum_col(MessageRole))
    author_name: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text)
    internal: Mapped[bool] = mapped_column(default=False)
    attachments: Mapped[list[Any]] = mapped_column(sa.JSON, default=list)


class SupportArticle(TenantMixin, TimestampMixin, Base):
    __tablename__ = "support_articles"
    __table_args__ = (UniqueConstraint("tenant_id", "slug"),)
    id: Mapped[str] = _pk()
    slug: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[Category] = mapped_column(enum_col(Category))
    tags: Mapped[list[Any]] = mapped_column(sa.JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text)


class Incident(TenantMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_tenant_status", "tenant_id", "status"),)
    id: Mapped[str] = _pk()
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(32), default="investigating")
    severity: Mapped[Severity] = mapped_column(enum_col(Severity), default=Severity.medium)
    affected_services: Mapped[list[Any]] = mapped_column(sa.JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)


class WorkflowRun(TenantMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_tenant_ticket_started", "tenant_id", "ticket_id", "started_at"),
    )
    id: Mapped[str] = _pk()
    ticket_id: Mapped[str] = _fk("tickets")
    thread_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[WorkflowStatus] = mapped_column(
        enum_col(WorkflowStatus), default=WorkflowStatus.running
    )
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    token_usage: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)


class WorkflowEvent(TenantMixin, TimestampMixin, Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        Index(
            "ix_workflow_events_tenant_workflow_created", "tenant_id", "workflow_id", "created_at"
        ),
    )
    id: Mapped[str] = _pk()
    workflow_id: Mapped[str] = _fk("workflow_runs")
    ticket_id: Mapped[str] = _fk("tickets")
    event_type: Mapped[WorkflowEventType] = mapped_column(enum_col(WorkflowEventType))
    node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)


class ResolutionAction(TenantMixin, TimestampMixin, Base):
    __tablename__ = "resolution_actions"
    # FR-16: a key that already succeeded is never acted on twice.
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)
    id: Mapped[str] = _pk()
    ticket_id: Mapped[str] = _fk("tickets")
    workflow_id: Mapped[str] = _fk("workflow_runs")
    tool: Mapped[str] = mapped_column(String(64))
    arguments: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    status: Mapped[ResolutionActionStatus] = mapped_column(
        enum_col(ResolutionActionStatus), default=ResolutionActionStatus.planned
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(default=False)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    verification: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)


class ApprovalRequest(TenantMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (Index("ix_approval_requests_tenant_status", "tenant_id", "status"),)
    id: Mapped[str] = _pk()
    ticket_id: Mapped[str] = _fk("tickets")
    workflow_id: Mapped[str] = _fk("workflow_runs")
    action: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(16), default="high")
    reason: Mapped[str] = mapped_column(Text, default="")
    requested_by: Mapped[str] = mapped_column(String(64), default="ai")
    status: Mapped[ApprovalStatus] = mapped_column(
        enum_col(ApprovalStatus), default=ApprovalStatus.pending
    )
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)
    # FR-24: an undecided approval expires and escalates.
    expires_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)


class Escalation(TenantMixin, TimestampMixin, Base):
    __tablename__ = "escalations"
    __table_args__ = (Index("ix_escalations_tenant_status", "tenant_id", "status"),)
    id: Mapped[str] = _pk()
    ticket_id: Mapped[str] = _fk("tickets")
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    status: Mapped[EscalationStatus] = mapped_column(
        enum_col(EscalationStatus), default=EscalationStatus.open
    )
    created_by: Mapped[str] = mapped_column(String(200), default="ai")
    assigned_team: Mapped[str] = mapped_column(String(100), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(_dt(), nullable=True)


class CustomerMemory(TenantMixin, TimestampMixin, Base):
    __tablename__ = "customer_memory"
    __table_args__ = (
        Index("ix_customer_memory_tenant_customer_type", "tenant_id", "customer_id", "memory_type"),
    )
    id: Mapped[str] = _pk()
    customer_id: Mapped[str] = _fk("customers")
    memory_type: Mapped[MemoryType] = mapped_column(enum_col(MemoryType))
    content: Mapped[str] = mapped_column(Text)
    source_ticket_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)


class AuditLog(TenantMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),)
    id: Mapped[str] = _pk()
    actor: Mapped[str] = mapped_column(String(200), default="")
    actor_type: Mapped[str] = mapped_column(String(32), default="user")
    action: Mapped[str] = mapped_column(String(200))
    resource_type: Mapped[str] = mapped_column(String(64), default="")
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    details: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    request_id: Mapped[str] = mapped_column(String(64), default="")
