import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.models.entities import DEMO_TENANT_ID, Base
from app.schemas.common import Category, Channel, Severity, TicketStatus

DATA_TABLES = sorted(set(Base.metadata.tables) - {"tenants"})


def test_the_model_has_the_sixteen_data_tables_plus_tenants():
    assert set(Base.metadata.tables) == {
        "tenants",
        "profiles",
        "customers",
        "subscriptions",
        "workspaces",
        "products",
        "tickets",
        "ticket_messages",
        "support_articles",
        "incidents",
        "workflow_runs",
        "workflow_events",
        "resolution_actions",
        "approval_requests",
        "escalations",
        "customer_memory",
        "audit_logs",
    }


@pytest.mark.parametrize("name", DATA_TABLES)
def test_every_data_table_has_a_not_null_indexed_tenant_id(name):
    table = Base.metadata.tables[name]
    col = table.c.tenant_id
    assert col.nullable is False
    assert isinstance(col.type, sa.String) and col.type.length == 36
    single_index = any([c.name for c in ix.columns] == ["tenant_id"] for ix in table.indexes)
    assert col.index or single_index
    assert {fk.target_fullname for fk in col.foreign_keys} == {"tenants.id"}


@pytest.mark.parametrize("name", DATA_TABLES)
def test_tenant_id_is_the_first_column_of_every_composite_index_and_unique_constraint(name):
    table = Base.metadata.tables[name]
    for ix in table.indexes:
        cols = [c.name for c in ix.columns]
        if len(cols) >= 2:
            assert cols[0] == "tenant_id", ix.name
    for con in table.constraints:
        if isinstance(con, sa.UniqueConstraint) and len(con.columns) >= 2:
            assert [c.name for c in con.columns][0] == "tenant_id", con.name


def test_every_primary_key_is_a_string36_uuid():
    for table in Base.metadata.tables.values():
        (pk,) = table.primary_key.columns
        assert isinstance(pk.type, sa.String) and pk.type.length == 36, table.name


def test_no_column_uses_a_postgres_only_type():
    banned = (postgresql.JSONB, postgresql.UUID, postgresql.ARRAY, postgresql.CITEXT)
    for table in Base.metadata.tables.values():
        for col in table.columns:
            assert not isinstance(col.type, banned), f"{table.name}.{col.name}"


def test_the_demo_tenant_id_is_a_fixed_valid_uuid():
    assert str(uuid.UUID(DEMO_TENANT_ID)) == DEMO_TENANT_ID


def test_enum_columns_use_the_common_vocabulary():
    t = Base.metadata.tables["tickets"]
    for col, enum in (
        ("status", TicketStatus),
        ("severity", Severity),
        ("category", Category),
        ("channel", Channel),
    ):
        assert list(t.c[col].type.enums) == [m.value for m in enum], col
