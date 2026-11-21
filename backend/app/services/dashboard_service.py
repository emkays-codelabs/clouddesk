"""Dashboard summary: counts and recent tickets for the console home (F12)."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.approvals import ApprovalRepository, EscalationRepository
from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketRepository
from app.schemas.common import Category, Severity
from app.schemas.dashboard import DashboardSummary
from app.services.ticket_service import _to_summary

RECENT_LIMIT = 5


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; they were stored as UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def get_summary(session: AsyncSession) -> DashboardSummary:
    tickets = TicketRepository(session)
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    severities = await tickets.count_by_severity()
    categories = await tickets.count_by_category()
    spans = await tickets.resolution_spans()
    minutes = [(_as_utc(done) - _as_utc(start)).total_seconds() / 60 for start, done in spans]
    recent, _ = await tickets.list(page=1, page_size=RECENT_LIMIT)
    names = await CustomerRepository(session).get_many(list({t.customer_id for t in recent}))
    return DashboardSummary(
        open_tickets=await tickets.count_open(),
        resolved_today=await tickets.count_resolved_since(midnight),
        pending_approvals=await ApprovalRepository(session).count_pending(),
        escalations_open=await EscalationRepository(session).count_open(),
        avg_resolution_minutes=round(sum(minutes) / len(minutes), 1) if minutes else 0.0,
        by_severity={s.value: severities.get(s, 0) for s in Severity},
        by_category={c.value: categories.get(c, 0) for c in Category},
        recent_tickets=[_to_summary(t, names[t.customer_id].name) for t in recent],
    )
