"""P2-4: the seed service. It writes through the repositories, once, in one transaction."""

import json
import shutil
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.models.entities import DEMO_TENANT_ID, Base
from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.services import seed_service
from app.services.seed_service import bootstrap_demo_data, load_sample_data, main

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data"


@pytest.fixture
async def engine(tmp_path):
    eng = get_engine(f"sqlite+aiosqlite:///{(tmp_path / 'seed.db').as_posix()}")
    await create_tables(eng)
    yield eng
    await dispose_engine()  # Windows keeps the file open until the engine is disposed


@pytest.fixture
def sessionmaker(engine):
    return get_sessionmaker(engine)


async def _counts(engine) -> dict[str, int]:
    async with engine.connect() as conn:
        return {
            name: (await conn.execute(sa.select(sa.func.count()).select_from(table))).scalar_one()
            for name, table in Base.metadata.tables.items()
        }


async def test_bootstrap_on_an_empty_database_loads_every_file(engine, sessionmaker):
    report = await bootstrap_demo_data(sessionmaker, SAMPLE)

    counts = await _counts(engine)
    assert report.loaded is True
    assert counts["profiles"] == 3 and report.profiles == 3
    assert counts["customers"] == 8
    assert counts["subscriptions"] == 8
    assert counts["workspaces"] == 8
    assert counts["tickets"] == 13
    assert counts["ticket_messages"] == 13
    assert counts["incidents"] == 2
    assert counts["products"] == 5
    assert (report.customers, report.tickets, report.messages) == (8, 13, 13)
    async with sessionmaker() as session:
        ticket = await TicketRepository(session).get_by_number("CD-1002")
        first = (await TicketMessageRepository(session).list_for_ticket(ticket.id))[0]
        assert first.role == "customer" and first.body == ticket.body


async def test_a_second_bootstrap_adds_no_rows(engine, sessionmaker, monkeypatch):
    await bootstrap_demo_data(sessionmaker, SAMPLE)
    before = await _counts(engine)

    # The emptiness check must stop the load itself; the unique keys are only a backstop.
    async def must_not_run(*_args, **_kwargs):
        raise AssertionError("the load ran against a seeded database")

    monkeypatch.setattr(seed_service, "_load", must_not_run)

    report = await bootstrap_demo_data(sessionmaker, SAMPLE)

    assert report.loaded is False and report.reason == "not_empty"
    assert await _counts(engine) == before


async def test_bootstrap_is_skipped_when_demo_mode_is_false(engine, sessionmaker, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")

    report = await bootstrap_demo_data(sessionmaker, SAMPLE)

    assert report.loaded is False and report.reason == "demo_mode_off"
    assert sum((await _counts(engine)).values()) == 0


async def test_bootstrap_is_skipped_when_the_database_already_has_a_customer(engine, sessionmaker):
    async with sessionmaker() as session:
        from app.repositories.tenants import TenantRepository

        await TenantRepository(session).ensure(DEMO_TENANT_ID, "Demo")
        await CustomerRepository(session).create(name="Existing", email="x@existing.example")
        await session.commit()
    before = await _counts(engine)

    report = await bootstrap_demo_data(sessionmaker, SAMPLE)

    assert report.loaded is False and report.reason == "not_empty"
    assert await _counts(engine) == before


async def test_ids_are_deterministic_across_two_fresh_databases(tmp_path):
    ids = []
    for name in ("a.db", "b.db"):
        eng = get_engine(f"sqlite+aiosqlite:///{(tmp_path / name).as_posix()}")
        await create_tables(eng)
        maker = get_sessionmaker(eng)
        await bootstrap_demo_data(maker, SAMPLE)
        async with maker() as session:
            ticket = await TicketRepository(session).get_by_number("CD-1002")
            ids.append(ticket.id)
        await dispose_engine()

    assert ids[0] == ids[1]
    assert str(uuid.UUID(ids[0])) == ids[0]  # a valid UUID, because Postgres columns are uuid


async def test_every_seeded_row_belongs_to_the_demo_tenant(engine, sessionmaker):
    await bootstrap_demo_data(sessionmaker, SAMPLE)

    async with engine.connect() as conn:
        for name, table in Base.metadata.tables.items():
            if "tenant_id" not in table.c:
                continue
            stray = (
                await conn.execute(
                    sa.select(sa.func.count())
                    .select_from(table)
                    .where(table.c.tenant_id != DEMO_TENANT_ID)
                )
            ).scalar_one()
            assert stray == 0, name


def _broken_copy(tmp_path: Path) -> Path:
    target = tmp_path / "sample"
    shutil.copytree(SAMPLE, target)
    tickets = json.loads((target / "tickets.json").read_text(encoding="utf-8"))
    tickets[1]["customer_key"] = "cust-does-not-exist"
    (target / "tickets.json").write_text(json.dumps(tickets), encoding="utf-8")
    return target


async def test_a_bad_record_loads_nothing(engine, sessionmaker, tmp_path):
    broken = _broken_copy(tmp_path)

    with pytest.raises(ValueError, match="CD-1002"):
        await bootstrap_demo_data(sessionmaker, broken)

    assert sum((await _counts(engine)).values()) == 0


async def test_a_failure_part_way_through_the_writes_rolls_everything_back(
    engine, sessionmaker, monkeypatch
):
    original = TicketRepository.create
    calls = 0

    async def flaky(self, **fields):
        nonlocal calls
        calls += 1
        if calls == 5:
            raise RuntimeError("disk full")
        return await original(self, **fields)

    monkeypatch.setattr(TicketRepository, "create", flaky)

    with pytest.raises(RuntimeError):
        await bootstrap_demo_data(sessionmaker, SAMPLE)

    assert sum((await _counts(engine)).values()) == 0


def test_load_sample_data_parses_and_cross_checks_without_touching_a_database():
    data = load_sample_data(SAMPLE)

    assert len(data.tickets) == 13 and len(data.customers) == 8
    assert len(data.previous_resolutions) >= 1  # validated here, never loaded into a table


async def test_ticket_created_at_comes_from_the_file(sessionmaker):
    await bootstrap_demo_data(sessionmaker, SAMPLE)

    async with sessionmaker() as session:
        tickets, total = await TicketRepository(session).list(page_size=100)

    assert total == 13
    assert [t.ticket_number for t in tickets][0] == "CD-1013"  # newest first
    assert tickets[-1].ticket_number == "CD-1001"


async def test_the_cli_entry_point_seeds_an_empty_database_and_is_a_no_op_after(
    engine, monkeypatch, capsys
):
    monkeypatch.setenv("DATABASE_URL", str(engine.url.render_as_string(hide_password=False)))
    monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE))

    assert await main() == 0
    assert "seeded" in capsys.readouterr().out.lower()
    assert await main() == 0
    assert "already seeded" in capsys.readouterr().out.lower()

    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    assert await main() == 1
    assert "DEMO_MODE" in capsys.readouterr().out


def test_the_module_exposes_a_namespace_for_deterministic_ids():
    assert isinstance(seed_service.SEED_NAMESPACE, uuid.UUID)
