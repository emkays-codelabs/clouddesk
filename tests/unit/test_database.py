from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.models.entities import DEMO_TENANT_ID, Base, Customer, Tenant, Ticket, TicketMessage


@pytest.fixture
async def engine(tmp_path):
    eng = get_engine(f"sqlite+aiosqlite:///{tmp_path / 'nested' / 't.db'}")
    yield eng
    # Windows keeps the file open until the engine is disposed.
    await dispose_engine()


async def _seed_customer(session) -> Customer:
    session.add(Tenant(id=DEMO_TENANT_ID, name="Demo"))
    # No relationship() links the models, so the unit of work will not order the inserts for us.
    await session.flush()
    customer = Customer(tenant_id=DEMO_TENANT_ID, name="Ada", email="ada@example.com")
    session.add(customer)
    await session.flush()
    return customer


async def test_create_tables_builds_every_table_on_an_empty_sqlite_file(engine):
    await create_tables(engine)
    async with engine.connect() as conn:
        names = await conn.run_sync(lambda c: sa.inspect(c).get_table_names())
    assert set(names) == set(Base.metadata.tables)


async def test_create_tables_is_idempotent(engine):
    await create_tables(engine)
    await create_tables(engine)


async def test_create_tables_creates_a_missing_parent_directory(engine, tmp_path):
    await create_tables(engine)
    assert (Path(tmp_path) / "nested" / "t.db").exists()


async def test_a_ticket_and_its_first_message_round_trip(engine):
    await create_tables(engine)
    maker = get_sessionmaker(engine)
    async with maker() as session:
        customer = await _seed_customer(session)
        ticket = Ticket(
            tenant_id=DEMO_TENANT_ID,
            customer_id=customer.id,
            ticket_number="CD-1001",
            subject="SSO fails",
            body="Cannot log in",
            channel="web",
        )
        session.add(ticket)
        await session.flush()
        session.add(
            TicketMessage(
                tenant_id=DEMO_TENANT_ID, ticket_id=ticket.id, role="customer", body="Cannot log in"
            )
        )
        await session.commit()
    async with maker() as session:
        got = (await session.execute(sa.select(Ticket))).scalar_one()
        msgs = (await session.execute(sa.select(TicketMessage))).scalars().all()
    assert got.status == "new"
    assert len(got.id) == 36
    assert [m.ticket_id for m in msgs] == [got.id]


async def test_an_unknown_status_is_rejected_by_the_database(engine):
    await create_tables(engine)
    async with get_sessionmaker(engine)() as session:
        customer = await _seed_customer(session)
        await session.commit()
        with pytest.raises(IntegrityError):
            await session.execute(
                sa.text(
                    "INSERT INTO tickets (id, tenant_id, ticket_number, customer_id, subject, body,"
                    " status, channel, tags, escalation_required, approval_status)"
                    " VALUES ('x', :t, 'CD-1', :c, 's', 'b', 'bogus',"
                    " 'web', '[]', 0, 'not_required')"
                ),
                {"t": DEMO_TENANT_ID, "c": customer.id},
            )


async def test_sqlite_enforces_foreign_keys(engine):
    await create_tables(engine)
    async with get_sessionmaker(engine)() as session:
        session.add(Customer(tenant_id=DEMO_TENANT_ID, name="Ada", email="a@example.com"))
        with pytest.raises(IntegrityError):
            await session.commit()


def test_core_does_not_import_agents():
    src = (Path(__file__).resolve().parents[2] / "backend/app/core/database.py").read_text(
        encoding="utf-8"
    )
    assert "agents" not in src.replace("agents/", "")
