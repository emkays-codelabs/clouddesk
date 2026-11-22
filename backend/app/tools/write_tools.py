"""Write tools (F9). Writes go through repositories and the integration mocks, then are read back.

`update_ticket` and `create_escalation` need no approval; `reset_demo_setting` and
`create_refund_request` do (policy decides, not this module). Each returns `Verified`: its result
plus the read-back of the record. Idempotency is the registry's job, via `DbIdempotencyStore`.
Failures raise, and the registry turns them into `ToolResult(ok=False)`.
"""

from typing import Any

from app.repositories.approvals import EscalationRepository
from app.repositories.customers import SubscriptionRepository, WorkspaceRepository
from app.repositories.tickets import TicketRepository
from app.schemas.common import Category, Severity, TicketStatus
from app.tools.context import ToolContext
from app.tools.registry import Verified, stable_hash

WRITE_TOOL_NAMES = (
    "update_ticket",
    "create_escalation",
    "reset_demo_setting",
    "create_refund_request",
)


def build_write_tools(ctx: ToolContext) -> list[Any]:
    async def update_ticket(
        ticket_id: str,
        status: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        assigned_to: str | None = None,
    ) -> Verified:
        """Update a ticket's status, severity, category or assignee. No approval needed.

        Returns {ticket_id, updated: {field: value}}, with a read-back of those fields.
        """
        changes: dict[str, Any] = {}
        if status is not None:
            changes["status"] = TicketStatus(status)
        if severity is not None:
            changes["severity"] = Severity(severity)
        if category is not None:
            changes["category"] = Category(category)
        if assigned_to is not None:
            changes["assigned_to"] = assigned_to
        if not changes:
            raise ValueError("nothing to update")
        async with ctx.session_factory() as session:
            repo = TicketRepository(session)
            if await repo.update(ticket_id, **changes) is None:
                raise LookupError(f"ticket not found: {ticket_id}")
            await session.commit()
        async with ctx.session_factory() as session:
            row = await TicketRepository(session).get(ticket_id)
        readback = {
            k: (str(getattr(row, k)) if k != "assigned_to" else row.assigned_to) for k in changes
        }
        expected = {k: str(v) for k, v in changes.items()}
        return Verified(
            data={"ticket_id": ticket_id, "updated": expected},
            verification={"verified": readback == expected, "readback": readback},
        )

    async def create_escalation(
        ticket_id: str, reason: str, assigned_team: str = "", priority: str = "normal"
    ) -> Verified:
        """Escalate a ticket to a named human team and mark the ticket escalated. No approval.

        Returns {escalation_id, ticket_id, assigned_team, priority}, with a read-back.
        """
        async with ctx.session_factory() as session:
            tickets = TicketRepository(session)
            if await tickets.get(ticket_id) is None:
                raise LookupError(f"ticket not found: {ticket_id}")
            esc = await EscalationRepository(session).create(
                ticket_id=ticket_id,
                reason=reason,
                priority=priority,
                assigned_team=assigned_team,
                created_by="ai",
            )
            await tickets.update(ticket_id, escalation_required=True, status=TicketStatus.escalated)
            await session.commit()
            escalation_id = esc.id
        async with ctx.session_factory() as session:
            stored = await EscalationRepository(session).get(escalation_id)
            ticket = await TicketRepository(session).get(ticket_id)
        verified = (
            stored is not None
            and stored.ticket_id == ticket_id
            and ticket is not None
            and ticket.escalation_required is True
        )
        return Verified(
            data={
                "escalation_id": escalation_id,
                "ticket_id": ticket_id,
                "assigned_team": assigned_team,
                "priority": priority,
            },
            verification={
                "verified": verified,
                "escalation_found": stored is not None,
                "ticket_status": str(ticket.status) if ticket else None,
            },
        )

    async def reset_demo_setting(workspace_id: str, setting: str) -> Verified:
        """Reset one workspace setting (for example `sso`) to its default. Needs approval.

        Returns {workspace_id, setting, state}, with a read-back of the setting state.
        """
        async with ctx.session_factory() as session:
            if await WorkspaceRepository(session).get(workspace_id) is None:
                raise LookupError(f"workspace not found: {workspace_id}")
        admin = ctx.integrations.workspace_admin
        await admin.reset_setting(workspace_id, setting)
        state = await admin.get_setting_state(workspace_id, setting)
        return Verified(
            data={"workspace_id": workspace_id, "setting": setting, "state": state},
            verification={"verified": state == "reset", "state": state},
        )

    async def create_refund_request(
        customer_id: str, subscription_id: str, amount: float, reason: str
    ) -> Verified:
        """Record a refund for a customer's subscription. Needs approval; no real money moves.

        Returns {refund_id, customer_id, subscription_id, amount}, with a read-back of the refund.
        """
        if amount <= 0:
            raise ValueError("refund amount must be positive")
        async with ctx.session_factory() as session:
            sub = await SubscriptionRepository(session).get_for_customer(customer_id)
        if sub is None or sub.id != subscription_id:
            raise ValueError("subscription does not belong to the customer")
        billing = ctx.integrations.billing
        key = stable_hash(
            {"customer_id": customer_id, "subscription_id": subscription_id, "amount": amount}
        )
        refund = await billing.create_refund(customer_id, subscription_id, amount, reason, key)
        stored = await billing.get_refund(refund["id"])
        verified = stored is not None and stored["amount"] == amount
        return Verified(
            data={
                "refund_id": refund["id"],
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "amount": amount,
            },
            verification={"verified": verified, "refund_found": stored is not None},
        )

    return [update_ticket, create_escalation, reset_demo_setting, create_refund_request]
