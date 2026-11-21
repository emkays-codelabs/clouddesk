"""A small parser for the constrained DDL format used in database/*.sql (not a general SQL parser).

Any statement it does not recognise raises ValueError, so format drift fails loudly.
"""

import re
from dataclasses import dataclass, field

TYPE_RE = r"(?:double precision|varchar\(\d+\)|uuid|text|integer|boolean|timestamptz|jsonb)"
KEYWORDS = r"(?:NOT NULL|PRIMARY KEY|REFERENCES|CHECK)\b"


@dataclass
class Column:
    type: str
    not_null: bool = False
    default: str | None = None
    check_values: list[str] | None = None
    references: tuple[str, str] | None = None


@dataclass
class Table:
    columns: dict[str, Column] = field(default_factory=dict)
    uniques: list[list[str]] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)


@dataclass
class Index:
    table: str
    columns: list[str]
    unique: bool = False


@dataclass
class Trigger:
    table: str
    timing: str
    event: str
    function: str


@dataclass
class Policy:
    name: str
    table: str
    command: str
    using: str
    check: str


@dataclass
class Insert:
    table: str
    columns: list[str]
    values: list[str]
    on_conflict: str | None


@dataclass
class Schema:
    tables: dict[str, Table] = field(default_factory=dict)
    indexes: dict[str, Index] = field(default_factory=dict)
    triggers: dict[str, Trigger] = field(default_factory=dict)
    rls_enabled: set[str] = field(default_factory=set)
    rls_forced: set[str] = field(default_factory=set)
    policies: list[Policy] = field(default_factory=list)
    inserts: list[Insert] = field(default_factory=list)
    functions: set[str] = field(default_factory=set)
    set_locals: list[tuple[str, str]] = field(default_factory=list)
    events: list[tuple[str, str, str]] = field(default_factory=list)
    sequence: list[str] = field(default_factory=list)


def _split_top(text: str, sep: str = ",") -> list[str]:
    """Split on sep outside parentheses and single quotes."""
    parts, depth, quoted, cur = [], 0, False, []
    for ch in text:
        if ch == "'":
            quoted = not quoted
        elif not quoted and ch == "(":
            depth += 1
        elif not quoted and ch == ")":
            depth -= 1
        if ch == sep and depth == 0 and not quoted:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _column(spec: str) -> tuple[str, Column]:
    name, rest = spec.split(None, 1)
    m = re.match(TYPE_RE, rest)
    if not m:
        raise ValueError(f"unknown column type in: {spec}")
    col = Column(type=m.group(0))
    rest = rest[m.end() :].strip()
    col.not_null = bool(re.search(r"\bNOT NULL\b", rest)) or "PRIMARY KEY" in rest
    if m := re.search(r"REFERENCES\s+(\w+)\((\w+)\)", rest):
        col.references = (m.group(1), m.group(2))
    if m := re.search(r"CHECK\s*\(\s*\w+\s+IN\s*\((.*?)\)\s*\)", rest):
        col.check_values = [v.strip().strip("'") for v in _split_top(m.group(1))]
    if m := re.search(rf"DEFAULT\s+(.*?)(?=\s+{KEYWORDS}|$)", rest):
        col.default = m.group(1).strip()
    return name, col


def parse(text: str) -> Schema:
    text = re.sub(r"--[^\n]*", "", text)
    text = re.sub(r"\$\$.*?\$\$", "$$BODY$$", text, flags=re.DOTALL)
    s = Schema()
    for raw in _split_top(text, ";"):
        flat = " ".join(raw.split())
        if not flat:
            continue
        _statement(s, flat)
    return s


def _statement(s: Schema, flat: str) -> None:
    up = flat.upper()
    if up in ("BEGIN", "COMMIT"):
        s.sequence.append(up.lower())
    elif m := re.match(r"CREATE TABLE (\w+) \((.*)\)$", flat, re.DOTALL):
        table = Table()
        for item in _split_top(m.group(2)):
            if um := re.match(r"UNIQUE \((.*)\)$", item):
                table.uniques.append([c.strip() for c in um.group(1).split(",")])
            else:
                name, col = _column(item)
                table.columns[name] = col
                if "PRIMARY KEY" in item:
                    table.primary_key.append(name)
        s.tables[m.group(1)] = table
        s.sequence.append("table")
    elif m := re.match(r"CREATE (UNIQUE )?INDEX (\w+) ON (\w+) \((.*)\)$", flat):
        cols = [c.strip() for c in m.group(4).split(",")]
        s.indexes[m.group(2)] = Index(m.group(3), cols, bool(m.group(1)))
        s.sequence.append("index")
    elif m := re.match(r"CREATE OR REPLACE FUNCTION (\w+)\(\)", flat):
        s.functions.add(m.group(1))
        s.sequence.append("function")
    elif m := re.match(
        r"CREATE TRIGGER (\w+) (BEFORE|AFTER) (\w+) ON (\w+) FOR EACH ROW "
        r"EXECUTE FUNCTION (\w+)\(\)$",
        flat,
    ):
        s.triggers[m.group(1)] = Trigger(m.group(4), m.group(2), m.group(3), m.group(5))
        s.sequence.append("trigger")
    elif m := re.match(r"ALTER TABLE (\w+) (ENABLE|FORCE) ROW LEVEL SECURITY$", flat):
        (s.rls_enabled if m.group(2) == "ENABLE" else s.rls_forced).add(m.group(1))
        s.sequence.append("rls")
    elif m := re.match(r"ALTER TABLE (\w+) ADD COLUMN (.*)$", flat):
        name, col = _column(m.group(2))
        s.tables[m.group(1)].columns[name] = col
        s.sequence.append("add_column")
    elif m := re.match(r"DROP POLICY IF EXISTS (\w+) ON (\w+)$", flat):
        s.events.append(("drop_policy", m.group(1), m.group(2)))
        s.sequence.append("drop_policy")
    elif m := re.match(
        r"CREATE POLICY (\w+) ON (\w+) FOR (\w+) USING \((.*)\) WITH CHECK \((.*)\)$", flat
    ):
        s.policies.append(Policy(m.group(1), m.group(2), *m.group(3, 4, 5)))
        s.events.append(("policy", m.group(1), m.group(2)))
        s.sequence.append("policy")
    elif m := re.match(r"SET LOCAL ([\w.]+) = '(.*)'$", flat):
        s.set_locals.append((m.group(1), m.group(2)))
        s.sequence.append("set_local")
    elif m := re.match(r"INSERT INTO (\w+) \((.*?)\) VALUES \((.*)\)(?: ON CONFLICT (.*))?$", flat):
        s.inserts.append(
            Insert(
                m.group(1),
                [c.strip() for c in m.group(2).split(",")],
                _split_top(m.group(3)),
                m.group(4),
            )
        )
        s.sequence.append("insert")
    elif re.match(r"CREATE EXTENSION IF NOT EXISTS \w+$", flat):
        s.sequence.append("extension")
    else:
        raise ValueError(f"unrecognised statement: {flat[:80]}")
