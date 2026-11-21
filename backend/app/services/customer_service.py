"""Customer use cases: list, and read one with subscription, workspace, tickets and memory (F4)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.customers import (
    CustomerRepository,
    SubscriptionRepository,
    WorkspaceRepository,
)
from app.repositories.memory import CustomerMemoryRepository
from app.repositories.tickets import TicketRepository
from app.schemas.customer import (
    Customer,
    CustomerDetail,
    CustomerMemory,
    CustomerPage,
    Subscription,
    Workspace,
)
from app.services.ticket_service import HISTORY_LIMIT, _to_summary

MEMORY_LIMIT = 10


class CustomerNotFound(Exception):
    pass


async def list_customers(
    session: AsyncSession, *, search: str | None, page: int, page_size: int
) -> CustomerPage:
    rows, total = await CustomerRepository(session).list(
        search=search, page=page, page_size=page_size
    )
    return CustomerPage(
        items=[Customer.model_validate(c) for c in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_customer(session: AsyncSession, customer_id: str) -> CustomerDetail:
    customer = await CustomerRepository(session).get(customer_id)
    if customer is None:
        raise CustomerNotFound
    subscription = await SubscriptionRepository(session).get_for_customer(customer.id)
    workspace = await WorkspaceRepository(session).get_for_customer(customer.id)
    tickets = await TicketRepository(session).list_for_customer(customer.id, limit=HISTORY_LIMIT)
    notes = await CustomerMemoryRepository(session).list_for_customer(
        customer.id, limit=MEMORY_LIMIT
    )
    return CustomerDetail(
        **Customer.model_validate(customer).model_dump(),
        subscription=Subscription.model_validate(subscription) if subscription else None,
        workspace=Workspace.model_validate(workspace) if workspace else None,
        tickets=[_to_summary(t, customer.name) for t in tickets],
        memory=[CustomerMemory.model_validate(n) for n in notes],
    )
