import pytest
from sql_ddl import parse

TABLE = """
-- a comment; with a semicolon
CREATE TABLE t (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    status varchar(32) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'closed')),
    score double precision,
    UNIQUE (tenant_id, status)
);
"""


def test_reads_a_table_with_columns_checks_references_and_uniques():
    t = parse(TABLE).tables["t"]
    assert list(t.columns) == ["id", "tenant_id", "status", "score"]
    assert t.primary_key == ["id"]
    assert t.columns["id"].not_null and t.columns["id"].default == "gen_random_uuid()"
    assert t.columns["tenant_id"].references == ("tenants", "id")
    assert t.columns["status"].type == "varchar(32)"
    assert t.columns["status"].default == "'new'"
    assert t.columns["status"].check_values == ["new", "closed"]
    assert t.columns["score"].type == "double precision" and not t.columns["score"].not_null
    assert t.uniques == [["tenant_id", "status"]]


def test_reads_index_trigger_rls_and_policy_statements():
    s = parse(
        """
        CREATE INDEX ix_t_a ON t (tenant_id, status);
        CREATE UNIQUE INDEX ux_t ON t (a);
        CREATE TRIGGER trg_t BEFORE UPDATE ON t FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        ALTER TABLE t ENABLE ROW LEVEL SECURITY;
        ALTER TABLE t FORCE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS p ON t;
        CREATE POLICY p ON t FOR ALL USING (a = f('x')::uuid) WITH CHECK (a = f('x')::uuid);
        BEGIN;
        SET LOCAL app.tenant_id = 'abc';
        INSERT INTO t (id, name) VALUES ('1', 'a, b') ON CONFLICT (id) DO NOTHING;
        COMMIT;
        """
    )
    assert s.indexes["ix_t_a"].columns == ["tenant_id", "status"]
    assert s.indexes["ux_t"].unique
    assert s.triggers["trg_t"].table == "t" and s.triggers["trg_t"].function == "set_updated_at"
    assert "t" in s.rls_enabled and "t" in s.rls_forced
    assert s.policies[0].using == "a = f('x')::uuid" and s.policies[0].check == s.policies[0].using
    assert s.events[0] == ("drop_policy", "p", "t")
    assert s.inserts[0].columns == ["id", "name"] and s.inserts[0].values == ["'1'", "'a, b'"]
    assert s.inserts[0].on_conflict == "(id) DO NOTHING"
    assert s.set_locals == [("app.tenant_id", "abc")]
    assert s.sequence == [
        "index", "index", "trigger", "rls", "rls", "drop_policy", "policy",
        "begin", "set_local", "insert", "commit",
    ]  # fmt: skip


def test_ignores_comments_and_dollar_quoted_bodies():
    s = parse(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN  -- inner; semicolons; stay opaque
            NEW.updated_at = now(); RETURN NEW;
        END;
        $$;
        """
    )
    assert s.functions == {"set_updated_at"}
    assert s.sequence == ["function"]


def test_fails_loudly_on_a_statement_it_does_not_understand():
    with pytest.raises(ValueError, match="GRANT"):
        parse("GRANT ALL ON t TO someone;")


def test_add_column_extends_an_existing_table():
    s = parse(TABLE + "ALTER TABLE t ADD COLUMN note text NOT NULL DEFAULT '';")
    assert s.tables["t"].columns["note"].not_null
    assert s.tables["t"].columns["note"].default == "''"
