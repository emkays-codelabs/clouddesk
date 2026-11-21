import hashlib
import re
from pathlib import Path

from sql_ddl import parse

DB = Path(__file__).resolve().parents[2] / "database"
MIGRATIONS = sorted((DB / "migrations").glob("*.sql"))
# Rule 12: an applied migration is never edited. Add each new file here with its hash.
APPLIED = {
    "0001_initial.sql": "c798964be6dfd974b97ffbcc35dfd18edbc134ca925d6846b4b847bfcc42dcf2",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_migration_names_are_numbered_from_0001_without_a_gap():
    assert MIGRATIONS, "no migrations"
    for i, m in enumerate(MIGRATIONS, start=1):
        assert re.fullmatch(r"\d{4}_[a-z0-9_]+\.sql", m.name), m.name
        assert int(m.name[:4]) == i, f"gap before {m.name}"


def test_the_first_migration_creates_every_data_table_with_tenant_id_inline():
    first = parse(read(MIGRATIONS[0]))
    schema = parse(read(DB / "schema.sql"))
    assert set(first.tables) == set(schema.tables)
    for name, t in first.tables.items():
        if name != "tenants":
            assert "tenant_id" in t.columns, name


def test_no_migration_adds_tenant_id_later():
    for m in MIGRATIONS:
        assert not re.search(r"ADD\s+COLUMN\s+tenant_id", read(m), re.IGNORECASE), m.name


def test_migrations_in_order_produce_schema_sql():
    migrated = parse("\n".join(read(m) for m in MIGRATIONS))
    expected = parse(read(DB / "schema.sql") + "\n" + read(DB / "rls_policies.sql"))
    assert migrated.tables == expected.tables
    assert migrated.indexes == expected.indexes
    assert migrated.triggers == expected.triggers
    assert migrated.functions == expected.functions
    assert migrated.policies == expected.policies
    assert migrated.rls_enabled == expected.rls_enabled
    assert migrated.rls_forced == expected.rls_forced


def test_applied_migrations_are_unchanged():
    for m in MIGRATIONS:
        digest = hashlib.sha256(read(m).replace("\r\n", "\n").encode()).hexdigest()
        assert APPLIED.get(m.name) == digest, f"{m.name} changed or is not pinned in APPLIED"
