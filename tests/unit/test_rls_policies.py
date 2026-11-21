from pathlib import Path

import pytest
from sql_ddl import parse

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = parse((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
RLS = parse((ROOT / "database" / "rls_policies.sql").read_text(encoding="utf-8"))
DATA_TABLES = sorted(n for n, t in SCHEMA.tables.items() if "tenant_id" in t.columns)
EXPR = "tenant_id = current_setting('app.tenant_id')::uuid"


def norm(s: str) -> str:
    return " ".join(s.split())


@pytest.mark.parametrize("table", DATA_TABLES)
def test_every_data_table_has_rls_enabled_forced_and_keyed_on_tenant_id(table):
    assert table in RLS.rls_enabled and table in RLS.rls_forced
    policies = [p for p in RLS.policies if p.table == table]
    assert len(policies) == 1 and policies[0].command == "ALL"
    assert norm(policies[0].using) == EXPR
    assert norm(policies[0].check) == EXPR


def test_the_rls_table_set_equals_the_schema_data_table_set():
    covered = {p.table for p in RLS.policies} - {"tenants"}
    assert covered == set(DATA_TABLES)
    assert RLS.rls_enabled - {"tenants"} == set(DATA_TABLES)
    assert RLS.rls_forced - {"tenants"} == set(DATA_TABLES)


def test_the_tenants_table_is_scoped_by_its_own_id():
    (p,) = [p for p in RLS.policies if p.table == "tenants"]
    assert norm(p.using) == "id = current_setting('app.tenant_id')::uuid"
    assert norm(p.check) == norm(p.using)
    assert "tenants" in RLS.rls_enabled and "tenants" in RLS.rls_forced


def test_the_policy_compares_uuid_with_uuid():
    for t in DATA_TABLES:
        assert SCHEMA.tables[t].columns["tenant_id"].type == "uuid"
    assert SCHEMA.tables["tenants"].columns["id"].type == "uuid"


def test_the_policy_file_is_rerunnable():
    pending = None
    for kind, name, table in [e for e in RLS.events if e[0] in ("drop_policy", "policy")]:
        if kind == "drop_policy":
            pending = (name, table)
        else:
            assert pending == (name, table), f"{name} on {table} not preceded by DROP POLICY"
            pending = None
