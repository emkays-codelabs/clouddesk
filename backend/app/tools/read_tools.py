"""Read-only support tools (F4, F5, F7). None of them writes.

Each is an async function whose docstring is the description the LLM and MCP clients see. They
are built per `ToolContext` and run only through `ToolRegistry.execute`. A missing record raises
`LookupError`, which the registry turns into `ToolResult(ok=False)`.
"""

from typing import Any

from app.repositories.customers import CustomerRepository, SubscriptionRepository
from app.repositories.reference import IncidentRepository
from app.repositories.tickets import TicketRepository
from app.tools.context import ToolContext

READ_TOOL_NAMES = (
    "get_customer",
    "get_subscription",
    "get_ticket_history",
    "search_docs",
    "check_service_status",
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def build_read_tools(ctx: ToolContext) -> list[Any]:
    async def get_customer(customer_id: str) -> dict[str, Any]:
        """Load a customer's profile by id.

        Returns {id, name, email, company, plan_name, status, region, lifetime_value, created_at}.
        """
        async with ctx.session_factory() as session:
            row = await CustomerRepository(session).get(customer_id)
        if row is None:
            raise LookupError(f"customer not found: {customer_id}")
        return {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "company": row.company,
            "plan_name": row.plan_name,
            "status": row.status,
            "region": row.region,
            "lifetime_value": row.lifetime_value,
            "created_at": _iso(row.created_at),
        }

    async def get_subscription(customer_id: str) -> dict[str, Any]:
        """Load a customer's current subscription: plan, seats, spend, storage and API limits.

        Returns {id, customer_id, plan, seats, status, renews_at, mrr, storage_quota_gb,
        storage_used_gb, api_rate_limit}.
        """
        async with ctx.session_factory() as session:
            row = await SubscriptionRepository(session).get_for_customer(customer_id)
        if row is None:
            raise LookupError(f"subscription not found for customer: {customer_id}")
        return {
            "id": row.id,
            "customer_id": row.customer_id,
            "plan": row.plan,
            "seats": row.seats,
            "status": row.status,
            "renews_at": _iso(row.renews_at),
            "mrr": row.mrr,
            "storage_quota_gb": row.storage_quota_gb,
            "storage_used_gb": row.storage_used_gb,
            "api_rate_limit": row.api_rate_limit,
        }

    async def get_ticket_history(
        customer_id: str, exclude_ticket_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """List a customer's previous tickets, newest first.

        Returns a list of {id, ticket_number, subject, status, severity, category, channel,
        escalation_required, created_at, updated_at}.
        """
        async with ctx.session_factory() as session:
            rows = await TicketRepository(session).list_for_customer(
                customer_id, exclude_ticket_id=exclude_ticket_id, limit=limit
            )
        return [
            {
                "id": t.id,
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "status": str(t.status),
                "severity": str(t.severity) if t.severity else None,
                "category": str(t.category) if t.category else None,
                "channel": str(t.channel),
                "escalation_required": bool(t.escalation_required),
                "created_at": _iso(t.created_at),
                "updated_at": _iso(t.updated_at),
            }
            for t in rows
        ]

    async def search_docs(query: str, top_k: int = 5, mode: str = "hybrid") -> list[dict[str, Any]]:
        """Search the knowledge base (hybrid, semantic or keyword) and return cited evidence.

        Returns a list of {id, title, source, snippet, score, url, article_id}; `source` is a
        `kb://slug#section` citation.
        """
        return await ctx.search(query, top_k, mode)

    async def check_service_status(service: str | None = None) -> dict[str, Any]:
        """Check for active incidents, optionally for one service (for example `sso` or `api`).

        Returns {status: "operational" | "degraded", incidents: [{id, title, status, severity,
        affected_services, description}]}, plus `service` when one was asked for.
        """
        async with ctx.session_factory() as session:
            active = await IncidentRepository(session).list_active()
        wanted = service.strip().lower() if service else None
        incidents = [
            {
                "id": i.id,
                "title": i.title,
                "status": i.status,
                "severity": str(i.severity),
                "affected_services": list(i.affected_services),
                "description": i.description,
            }
            for i in active
            if wanted is None or wanted in {str(s).lower() for s in i.affected_services}
        ]
        out: dict[str, Any] = {
            "status": "degraded" if incidents else "operational",
            "incidents": incidents,
        }
        if service:
            out["service"] = service
        return out

    return [get_customer, get_subscription, get_ticket_history, search_docs, check_service_status]
