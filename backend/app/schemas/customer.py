"""Customer response types (docs/design/06_API_CONTRACT.md, Customers)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CustomerStatus, MemoryType, Plan
from app.schemas.ticket import TicketSummary


class Customer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    company: str = ""
    plan_name: str
    status: CustomerStatus
    created_at: datetime
    region: str = ""
    lifetime_value: float = 0.0


class Subscription(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    plan: Plan
    seats: int
    status: str
    renews_at: datetime | None = None
    mrr: float
    storage_quota_gb: float
    storage_used_gb: float
    api_rate_limit: int


class Workspace(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    name: str
    member_count: int
    storage_used_gb: float
    integrations: list[str] = Field(default_factory=list)
    sso_enabled: bool = False


class CustomerMemory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    memory_type: MemoryType
    content: str
    source_ticket_id: str | None = None
    confidence: float | None = None
    created_at: datetime


class CustomerDetail(Customer):
    subscription: Subscription | None = None
    workspace: Workspace | None = None
    tickets: list[TicketSummary] = Field(default_factory=list)
    memory: list[CustomerMemory] = Field(default_factory=list)


class CustomerPage(BaseModel):
    items: list[Customer]
    total: int
    page: int
    page_size: int
