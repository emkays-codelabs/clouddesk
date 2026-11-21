"""TicketDetail is its own module so customer.py can import TicketSummary without a cycle."""

from pydantic import Field

from app.schemas.customer import Customer, Subscription
from app.schemas.ticket import Ticket, TicketMessage, TicketSummary
from app.schemas.workflow import Escalation, ResolutionAction, WorkflowState


class TicketDetail(Ticket):
    messages: list[TicketMessage] = Field(default_factory=list)
    customer: Customer
    subscription: Subscription | None = None
    history: list[TicketSummary] = Field(default_factory=list)
    workflow: WorkflowState | None = None
    resolution_actions: list[ResolutionAction] = Field(default_factory=list)
    escalation: Escalation | None = None
