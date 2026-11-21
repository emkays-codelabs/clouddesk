"""Ticket request and response bodies (docs/design/06_API_CONTRACT.md, Tickets)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import (
    ApprovalStatus,
    Category,
    Channel,
    MessageRole,
    Severity,
    TicketStatus,
)


class Attachment(BaseModel):
    name: str
    url: str
    size: int


class TicketSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_number: str
    subject: str
    status: TicketStatus
    severity: Severity | None = None
    category: Category | None = None
    customer_id: str
    customer_name: str
    channel: Channel
    created_at: datetime
    updated_at: datetime
    escalation_required: bool = False
    approval_status: ApprovalStatus = ApprovalStatus.not_required


class Ticket(TicketSummary):
    body: str
    assigned_to: str | None = None
    resolved_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class TicketMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    role: MessageRole
    author_name: str
    body: str
    internal: bool = False
    attachments: list[Attachment] = Field(default_factory=list)
    created_at: datetime


class TicketPage(BaseModel):
    items: list[TicketSummary]
    total: int
    page: int
    page_size: int


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    channel: Channel = Channel.web


class TicketReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1)
    internal: bool = False


class TicketRequestInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[str] = Field(min_length=1)


class TicketEscalate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)
    priority: Literal["normal", "urgent"] = "normal"


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus | None = None
    severity: Severity | None = None
    assigned_to: str | None = None
