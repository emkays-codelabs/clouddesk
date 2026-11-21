from pathlib import Path

from sql_ddl import parse

from app.models.entities import DEMO_TENANT_ID

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = parse((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
SEED = parse((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))


def test_seed_runs_in_one_transaction_with_the_tenant_set():
    seq = SEED.sequence
    assert seq[0] == "begin" and seq[-1] == "commit"
    assert seq[1] == "set_local" and set(seq[2:-1]) == {"insert"}
    assert SEED.set_locals == [("app.tenant_id", DEMO_TENANT_ID)]


def test_seed_inserts_the_demo_tenant_with_the_model_constant():
    (ins,) = SEED.inserts
    row = dict(zip(ins.columns, ins.values, strict=True))
    assert ins.table == "tenants" and row["id"] == f"'{DEMO_TENANT_ID}'"


def test_every_insert_targets_a_table_in_schema_sql_and_uses_its_columns():
    for ins in SEED.inserts:
        assert set(ins.columns) <= set(SCHEMA.tables[ins.table].columns)
        assert len(ins.columns) == len(ins.values)


def test_every_data_row_carries_the_demo_tenant_id():
    for ins in SEED.inserts:
        if ins.table == "tenants":
            continue
        row = dict(zip(ins.columns, ins.values, strict=True))
        assert row["tenant_id"] == f"'{DEMO_TENANT_ID}'"


def test_every_insert_is_idempotent():
    assert all(i.on_conflict and i.on_conflict.endswith("DO NOTHING") for i in SEED.inserts)
