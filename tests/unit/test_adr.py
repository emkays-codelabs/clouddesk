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


def test_decisions_d2_to_d6_are_recorded_as_accepted_and_not_built():
    # D2, D3, D5 and D6 were approved on 2026-11-27 but are not built; D4 is limited.
    texts = " ".join(_text(p) for p in _records())

    for decision in ("D2", "D3", "D4", "D5", "D6"):
        assert decision in texts
    for number in ("0008", "0009", "0011", "0012"):
        record = next(p for p in _records() if p.name.startswith(f"{number}-"))
        status = _text(record).split("## Context")[0].lower()
        assert "accepted" in status


def test_the_settled_tenancy_decision_d1_is_recorded_as_accepted():
    tenancy = next(p for p in _records() if "tenan" in p.name)

    assert "accepted" in _text(tenancy).split("## Context")[0].lower()


def test_model_tiering_d4_is_accepted_in_a_limited_form_with_no_gateway_service():
    record = next(p for p in _records() if p.name.startswith("0010-"))
    text = _text(record)
    status = text.split("## Context")[0].lower()

    assert "accepted in a limited form" in status and "owner" in status
    assert "no gateway service" in text.lower() or "does not add a gateway service" in text
    assert "llm_router.py" in text and "P9-9" in text and "P9-10" in text
