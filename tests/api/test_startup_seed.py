"""P2-4: the app lifespan creates tables and seeds the demo data (F4, F14)."""

import logging

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import dispose_engine, get_engine, get_sessionmaker
from app.main import create_app
from app.models.entities import Base
from app.repositories.customers import (
    CustomerRepository,
    SubscriptionRepository,
    WorkspaceRepository,
)
from app.repositories.tickets import TicketMessageRepository, TicketRepository


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'startup.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


def _start() -> None:
    """Enter and leave the app once, so the lifespan runs its startup and shutdown."""
    with TestClient(create_app()):
        pass


async def _inspect(url, work):
    engine = get_engine(url)
    try:
        async with get_sessionmaker(engine)() as session:
            return await work(session)
    finally:
        await dispose_engine()


async def _table_counts(url) -> dict[str, int]:
    engine = get_engine(url)
    try:
        async with engine.connect() as conn:
            return {
                name: (await conn.execute(sa.select(sa.func.count()).select_from(t))).scalar_one()
                for name, t in Base.metadata.tables.items()
            }
    finally:
        await dispose_engine()


async def test_startup_on_an_empty_database_loads_13_tickets_and_8_customers(db_url):
    _start()

    async def totals(session):
        return (
            (await TicketRepository(session).list(page_size=1))[1],
            (await CustomerRepository(session).list(page_size=1))[1],
        )

    assert await _inspect(db_url, totals) == (13, 8)


async def test_a_second_startup_adds_no_rows(db_url):
    _start()
    first = await _table_counts(db_url)

    _start()

    assert await _table_counts(db_url) == first
    assert first["tickets"] == 13


async def test_cd_1002_and_its_customer_subscription_and_workspace_are_readable(db_url):
    _start()

    async def read(session):
        ticket = await TicketRepository(session).get_by_number("CD-1002")
        customer = await CustomerRepository(session).get(ticket.customer_id)
        subscription = await SubscriptionRepository(session).get_for_customer(customer.id)
        workspace = await WorkspaceRepository(session).get_for_customer(customer.id)
        messages = await TicketMessageRepository(session).list_for_ticket(ticket.id)
        return ticket, customer, subscription, workspace, messages

    ticket, customer, subscription, workspace, messages = await _inspect(db_url, read)

    assert ticket.subject.startswith("Refund")
    assert customer.company == "BrightPath Studio"
    assert subscription.seats == 8
    assert workspace.member_count == 5
    assert messages[0].body == ticket.body


def test_startup_survives_an_unusable_database_and_logs_no_secret(monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", "mysql://app:hunter2@db.example.com/x")

    with caplog.at_level(logging.ERROR):
        with TestClient(create_app()) as client:
            live = client.get("/health/live")
            ready = client.get("/health/ready")

    assert live.status_code == 200
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert errors
    # A traceback can echo the connection URL, so the startup error carries none.
    assert all(r.exc_info is None for r in errors)
    for text in (caplog.text, ready.text):
        assert "hunter2" not in text and "db.example.com" not in text


async def test_startup_with_demo_mode_off_creates_tables_but_loads_nothing(db_url, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")

    _start()

    counts = await _table_counts(db_url)
    assert set(counts) == set(Base.metadata.tables)  # tables exist
    assert sum(counts.values()) == 0
