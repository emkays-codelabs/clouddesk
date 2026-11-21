"""schema.sql must agree with the SQLAlchemy models. Text-checked: no Postgres runs."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from sql_ddl import parse

from app.models.entities import Base

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = parse((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
TABLES = sorted(Base.metadata.tables)
UPDATED_AT_TRIGGER = "set_updated_at"


def sql_type(col: sa.Column) -> str:
    t = col.type
    if isinstance(t, sa.Enum):  # before String: Enum subclasses it
        return "varchar(32)"
    if isinstance(t, sa.String) and not isinstance(t, sa.Text):
        return "uuid" if t.length == 36 else f"varchar({t.length})"
    return {
        sa.Text: "text",
        sa.Integer: "integer",
        sa.Float: "double precision",
        sa.Boolean: "boolean",
        sa.DateTime: "timestamptz",
        sa.JSON: "jsonb",
    }[type(t)]


def sql_default(col: sa.Column) -> str | None:
    if col.primary_key:
        return "gen_random_uuid()"
    if col.server_default is not None:
        return "now()"
    d = col.default
    if d is None:
        return None
    if d.is_callable:
        return {list: "'[]'::jsonb", dict: "'{}'::jsonb"}[type(d.arg(None))]
    v = d.arg
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):  # includes StrEnum members
        return f"'{v}'"
    return str(v)


def same_default(col: sa.Column, sql: str | None) -> bool:
    expected = sql_default(col)
    if expected is not None and sql is not None and isinstance(col.type, sa.Float):
        return float(expected) == float(sql)
    return expected == sql


def test_schema_sql_is_the_authority_for_the_table_count():
    assert len(SCHEMA.tables) == 17
    with_tenant = {n for n, t in SCHEMA.tables.items() if "tenant_id" in t.columns}
    assert len(with_tenant) == 16 and set(SCHEMA.tables) - with_tenant == {"tenants"}
    assert set(SCHEMA.tables) == set(Base.metadata.tables)


@pytest.mark.parametrize("name", TABLES)
def test_schema_sql_and_the_models_agree_on_tables_and_column_types(name):
    model, sql = Base.metadata.tables[name], SCHEMA.tables[name]
    assert list(sql.columns) == [c.name for c in model.columns]
    for col in model.columns:
        s = sql.columns[col.name]
        assert s.type == sql_type(col), f"{name}.{col.name}"
        assert s.not_null == (not col.nullable), f"{name}.{col.name} nullability"


@pytest.mark.parametrize("name", TABLES)
def test_enum_checks_list_exactly_the_common_vocabulary(name):
    for col in Base.metadata.tables[name].columns:
        s = SCHEMA.tables[name].columns[col.name]
        if isinstance(col.type, sa.Enum):
            assert s.check_values == list(col.type.enums), f"{name}.{col.name}"
        else:
            assert s.check_values is None, f"{name}.{col.name}"


@pytest.mark.parametrize("name", TABLES)
def test_defaults_agree_with_the_model(name):
    for col in Base.metadata.tables[name].columns:
        s = SCHEMA.tables[name].columns[col.name]
        assert same_default(col, s.default), f"{name}.{col.name}: {s.default!r}"


@pytest.mark.parametrize("name", TABLES)
def test_foreign_keys_agree(name):
    for col in Base.metadata.tables[name].columns:
        expected = {(fk.column.table.name, fk.column.name) for fk in col.foreign_keys}
        s = SCHEMA.tables[name].columns[col.name].references
        assert ({s} if s else set()) == expected, f"{name}.{col.name}"
        assert all(c == "id" for _, c in expected)


@pytest.mark.parametrize("name", sorted(set(TABLES) - {"tenants"}))
def test_tenant_id_is_uuid_not_null_references_tenants_and_is_indexed_on_every_data_table(name):
    c = SCHEMA.tables[name].columns["tenant_id"]
    assert c.type == "uuid" and c.not_null and c.references == ("tenants", "id")
    assert SCHEMA.indexes[f"ix_{name}_tenant_id"].columns == ["tenant_id"]


@pytest.mark.parametrize("name", TABLES)
def test_composite_indexes_and_uniques_match_the_model_and_lead_with_tenant_id(name):
    table = Base.metadata.tables[name]
    model_ix = {i.name: [c.name for c in i.columns] for i in table.indexes}
    sql_ix = {n: i.columns for n, i in SCHEMA.indexes.items() if i.table == name}
    assert sql_ix == model_ix
    model_uq = [
        [c.name for c in k.columns] for k in table.constraints if isinstance(k, sa.UniqueConstraint)
    ]
    assert sorted(SCHEMA.tables[name].uniques) == sorted(model_uq)
    if name != "tenants":
        for cols in [*sql_ix.values(), *model_uq]:
            assert cols[0] == "tenant_id"


def test_set_updated_at_is_defined_once_and_triggered_on_every_table():
    assert SCHEMA.functions == {UPDATED_AT_TRIGGER}
    assert sum(s == "function" for s in SCHEMA.sequence) == 1
    by_table = {}
    for t in SCHEMA.triggers.values():
        assert (t.timing, t.event, t.function) == ("BEFORE", "UPDATE", UPDATED_AT_TRIGGER)
        by_table[t.table] = by_table.get(t.table, 0) + 1
    assert by_table == dict.fromkeys(SCHEMA.tables, 1)
    assert all("updated_at" in t.columns for t in SCHEMA.tables.values())


def test_tables_are_created_after_the_tables_they_reference():
    seen: set[str] = set()
    for name, table in SCHEMA.tables.items():
        for c in table.columns.values():
            if c.references:
                assert c.references[0] in seen, f"{name} before {c.references[0]}"
        seen.add(name)
