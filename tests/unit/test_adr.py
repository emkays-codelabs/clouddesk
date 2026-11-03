"""P1-14: architecture decisions are recorded in docs/adr/, one file each, and indexed."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADR = ROOT / "docs" / "adr"
RECORD = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
STATUSES = {"accepted", "proposed", "superseded"}
SECTIONS = ["## Status", "## Context", "## Decision", "## Consequences"]


def _records() -> list[pathlib.Path]:
    return sorted(p for p in ADR.glob("*.md") if p.name != "README.md")


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_the_folder_and_its_index_exist():
    assert (ADR / "README.md").is_file()


def test_every_record_is_named_with_a_four_digit_number_and_a_slug():
    assert [p.name for p in _records() if not RECORD.match(p.name)] == []


def test_the_numbers_start_at_0001_and_have_no_gap():
    numbers = [int(RECORD.match(p.name).group(1)) for p in _records()]

    assert numbers == list(range(1, len(numbers) + 1))


def test_every_record_has_a_title_and_the_four_sections():
    problems = []
    for path in _records():
        text = _text(path)
        if not text.startswith(f"# ADR-{path.name[:4]}: "):
            problems.append(f"{path.name}: title")
        problems += [f"{path.name}: {s}" for s in SECTIONS if s not in text]

    assert problems == []


def test_every_status_is_one_the_index_defines():
    bad = []
    for path in _records():
        status = _text(path).split("## Status")[1].strip().split("\n")[0].strip().lower()
        if status.split()[0].rstrip(".,;:") not in STATUSES:
            bad.append(f"{path.name}: {status!r}")

    assert bad == []


def test_the_index_lists_every_record_and_nothing_else():
    index = _text(ADR / "README.md")
    linked = set(re.findall(r"\]\(([0-9]{4}-[a-z0-9-]+\.md)\)", index))

    assert linked == {p.name for p in _records()}


def test_the_undecided_questions_d2_to_d6_are_recorded_as_proposed_not_decided():
    texts = " ".join(_text(p) for p in _records())

    for decision in ("D2", "D3", "D4", "D5", "D6"):
        assert decision in texts
    proposed = [p for p in _records() if "proposed" in _text(p).split("## Context")[0].lower()]
    assert len(proposed) >= 5


def test_the_settled_tenancy_decision_d1_is_recorded_as_accepted():
    tenancy = next(p for p in _records() if "tenan" in p.name)

    assert "accepted" in _text(tenancy).split("## Context")[0].lower()
