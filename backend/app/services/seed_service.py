"""Demo data bootstrap (P2-4, F4, F14).

Loads `sample_data/*.json` through the repositories, in one transaction, only when `DEMO_MODE` is
on and the database holds no customers or tickets. Ids are `uuid5` of the record key, so a record
has the same id on every machine. `previous_resolutions.json` is validated but not loaded: no table
holds it yet (the Knowledge Agent reads it in Phase 9).

Run by hand with `make seed`, or by the app lifespan at startup.
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine, get_sessionmaker
from app.models.entities import DEMO_TENANT_ID
from app.repositories.customers import (
    CustomerRepository,
    SubscriptionRepository,
    WorkspaceRepository,
)
from app.repositories.reference import IncidentRepository, ProductRepository
from app.repositories.tenants import TenantRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.schemas.common import Category, Channel, MessageRole, Severity

logger = logging.getLogger(__name__)

# Fixed so a record keeps its id across machines and databases.
SEED_NAMESPACE = uuid.UUID("6f1c2f0e-8a54-4b1e-9d3a-0c10d5e5d001")

Plan = Literal["free", "pro", "business", "enterprise"]


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Customer(_Record):
    key: str
    name: str
    email: str
    company: str
    plan_name: Plan
    status: Literal["active", "trial", "past_due", "churned"]
    region: str
    lifetime_value: float


class _Subscription(_Record):
    customer_key: str
    plan: Plan
    seats: int
    status: str
    renews_at: datetime
    mrr: float
    storage_quota_gb: float
    storage_used_gb: float
    api_rate_limit: int


class _Workspace(_Record):
    customer_key: str
    name: str
    member_count: int
    storage_used_gb: float
    integrations: list[str]
    sso_enabled: bool


class _Ticket(_Record):
    ticket_number: str
    customer_key: str
    subject: str
    body: str
    channel: Channel
    created_at: datetime


class _Incident(_Record):
    key: str
    title: str
    status: Literal["investigating", "identified", "monitoring", "resolved"]
    severity: Severity
    affected_services: list[str]
    description: str
    started_at: datetime
    resolved_at: datetime | None


class _Product(_Record):
    slug: str
    name: str
    description: str
    features: list[str]


class _Resolution(_Record):
    key: str
    category: Category
    subject: str
    summary: str
    steps: list[str]
    resolution: str


class SampleData(_Record):
    customers: list[_Customer]
    subscriptions: list[_Subscription]
    workspaces: list[_Workspace]
    tickets: list[_Ticket]
    incidents: list[_Incident]
    products: list[_Product]
    previous_resolutions: list[_Resolution]


class SeedReport(BaseModel):
    loaded: bool
    reason: str = ""
    customers: int = 0
    subscriptions: int = 0
    workspaces: int = 0
    tickets: int = 0
    messages: int = 0
    incidents: int = 0
    products: int = 0


_FILES: dict[str, type[_Record]] = {
    "customers": _Customer,
    "subscriptions": _Subscription,
    "workspaces": _Workspace,
    "tickets": _Ticket,
    "incidents": _Incident,
    "products": _Product,
    "previous_resolutions": _Resolution,
}
_ID_FIELD = {
    "customers": "key",
    "subscriptions": "customer_key",
    "workspaces": "customer_key",
    "tickets": "ticket_number",
    "incidents": "key",
    "products": "slug",
    "previous_resolutions": "key",
}


def _id(kind: str, key: str) -> str:
    return str(uuid.uuid5(SEED_NAMESPACE, f"{kind}:{key}"))


def load_sample_data(directory: Path | str) -> SampleData:
    """Parse and cross-check every file. Reads files only; raises ValueError naming the record."""
    base = Path(directory)
    parsed: dict[str, list] = {}
    for name, model in _FILES.items():
        raw = json.loads((base / f"{name}.json").read_text(encoding="utf-8"))
        rows = []
        for index, item in enumerate(raw):
            is_dict = isinstance(item, dict)
            label = item.get(_ID_FIELD[name], f"#{index}") if is_dict else f"#{index}"
            try:
                rows.append(model.model_validate(item))
            except ValidationError as exc:
                raise ValueError(f"{name}.json: {label}: {exc.errors()[0]['msg']}") from None
        parsed[name] = rows

    customer_keys = {c.key for c in parsed["customers"]}
    for name in ("subscriptions", "workspaces", "tickets"):
        for row in parsed[name]:
            if row.customer_key not in customer_keys:
                label = getattr(row, _ID_FIELD[name])
                raise ValueError(f"{name}.json: {label}: unknown customer_key {row.customer_key}")
    for name in ("subscriptions", "workspaces"):
        keys = [r.customer_key for r in parsed[name]]
        if sorted(keys) != sorted(customer_keys):
            raise ValueError(f"{name}.json: needs exactly one record per customer")
    return SampleData(**parsed)


async def _load(session: AsyncSession, data: SampleData) -> SeedReport:
    customers = CustomerRepository(session)
    subscriptions = SubscriptionRepository(session)
    workspaces = WorkspaceRepository(session)
    products = ProductRepository(session)
    incidents = IncidentRepository(session)
    tickets = TicketRepository(session)
    messages = TicketMessageRepository(session)
    names: dict[str, str] = {}

    for c in data.customers:
        names[c.key] = c.name
        await customers.create(id=_id("customer", c.key), **c.model_dump(exclude={"key"}))
    for s in data.subscriptions:
        await subscriptions.create(
            id=_id("subscription", s.customer_key),
            customer_id=_id("customer", s.customer_key),
            **s.model_dump(exclude={"customer_key"}),
        )
    for w in data.workspaces:
        await workspaces.create(
            id=_id("workspace", w.customer_key),
            customer_id=_id("customer", w.customer_key),
            **w.model_dump(exclude={"customer_key"}),
        )
    for p in data.products:
        await products.create(id=_id("product", p.slug), **p.model_dump())
    for i in data.incidents:
        await incidents.create(id=_id("incident", i.key), **i.model_dump(exclude={"key"}))
    for t in data.tickets:
        ticket_id = _id("ticket", t.ticket_number)
        await tickets.create(
            id=ticket_id,
            customer_id=_id("customer", t.customer_key),
            **t.model_dump(exclude={"customer_key"}),
        )
        await messages.add(
            id=_id("message", f"{t.ticket_number}:1"),
            ticket_id=ticket_id,
            role=MessageRole.customer,
            author_name=names[t.customer_key],
            body=t.body,
            created_at=t.created_at,
        )
    await session.commit()  # the one commit: a failure above leaves the database untouched
    return SeedReport(
        loaded=True,
        customers=len(data.customers),
        subscriptions=len(data.subscriptions),
        workspaces=len(data.workspaces),
        tickets=len(data.tickets),
        messages=len(data.tickets),
        incidents=len(data.incidents),
        products=len(data.products),
    )


async def bootstrap_demo_data(
    sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    sample_dir: Path | str | None = None,
) -> SeedReport:
    settings = get_settings()
    if not settings.demo_mode:
        return SeedReport(loaded=False, reason="demo_mode_off")
    data = load_sample_data(sample_dir or settings.sample_data_dir)  # validate before any write

    async with (sessionmaker or get_sessionmaker())() as session:
        await TenantRepository(session).ensure(DEMO_TENANT_ID, "CloudDesk Demo")
        _, customer_total = await CustomerRepository(session).list(page_size=1)
        _, ticket_total = await TicketRepository(session).list(page_size=1)
        if customer_total or ticket_total:
            await session.rollback()
            return SeedReport(loaded=False, reason="not_empty")
        try:
            report = await _load(session, data)
        except IntegrityError:
            # Another worker seeded between our check and our commit (unique keys caught it).
            await session.rollback()
            return SeedReport(loaded=False, reason="not_empty")
        except BaseException:
            await session.rollback()
            raise
    logger.info("demo data seeded", extra={"counts": report.model_dump(exclude={"reason"})})
    return report


async def main() -> int:
    """`make seed`: create tables, then seed once. Never writes demo data outside DEMO_MODE."""
    if not get_settings().demo_mode:
        print("DEMO_MODE is false: refusing to load demo data.")
        return 1
    try:
        await create_tables()
        report = await bootstrap_demo_data()
    finally:
        await dispose_engine()
    if report.loaded:
        print(f"seeded: {report.customers} customers, {report.tickets} tickets")
    else:
        print("already seeded: the database is not empty, nothing added")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
