"""Customer Agent (F4): who is asking, what they pay for, what happened before. No model call.

Does: loads the customer, subscription and previous tickets through the read tools (the
`ToolRegistry`), the workspace through its repository and up to 10 memory notes through the memory
service, and returns a `CustomerContext`. A missing subscription or workspace is allowed; a missing
customer raises `LookupError`, because nothing downstream can run without one.
Must NOT: call a model, write anything, or load another customer's data.
"""

import time

from agents.specialists.common import ToolCallRecord, call_tool, elapsed_ms
from app.repositories.customers import WorkspaceRepository
from app.schemas.customer import Customer, Subscription, Workspace
from app.schemas.ticket import TicketSummary
from app.schemas.workflow import CustomerContext, TokenUsage
from app.services.customer_memory_service import build_memory_service
from app.tools.context import ToolContext
from app.tools.registry import ToolRegistry

MAX_NOTES = 10
HISTORY_LIMIT = 10


class CustomerAgent:
    def __init__(self, ctx: ToolContext, registry: ToolRegistry) -> None:
        self._ctx = ctx
        self._registry = registry

    async def run(
        self, customer_id: str, ticket_id: str | None = None
    ) -> tuple[CustomerContext, str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        calls: list[ToolCallRecord] = []
        found = await call_tool(self._registry, calls, "get_customer", {"customer_id": customer_id})
        if not found.ok:
            raise LookupError(found.error or f"customer not found: {customer_id}")
        customer = Customer.model_validate(found.data)

        sub = await call_tool(
            self._registry, calls, "get_subscription", {"customer_id": customer_id}
        )
        subscription = Subscription.model_validate(sub.data) if sub.ok else None

        history_args = {
            "customer_id": customer_id,
            "exclude_ticket_id": ticket_id,
            "limit": HISTORY_LIMIT,
        }
        hist = await call_tool(self._registry, calls, "get_ticket_history", history_args)
        extra = {"customer_id": customer_id, "customer_name": customer.name}
        previous = (
            [TicketSummary.model_validate({**row, **extra}) for row in hist.data] if hist.ok else []
        )

        async with self._ctx.session_factory() as session:
            row = await WorkspaceRepository(session).get_for_customer(customer_id)
            workspace = Workspace.model_validate(row) if row is not None else None
            notes = await build_memory_service(session).recall_customer(customer_id)

        context = CustomerContext(
            customer=customer,
            subscription=subscription,
            workspace=workspace,
            previous_tickets=previous,
            memory_notes=[f"{n.memory_type}: {n.content}" for n in notes[:MAX_NOTES]],
        )
        return context, "ok", TokenUsage(), elapsed_ms(started), calls
