"""P1-7: docs/ uses numbered short names, and nothing in the repository points at an old one."""

import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

# NN_NAME.ext: two-digit number so a plain listing is reading order, capitals and underscores only.
DOC_NAME = re.compile(r"^(\d{2})_[A-Z][A-Z0-9_]*\.(?:md|txt)$")

# BRD (why) -> PRD (what) -> HLD (how) -> LLD (detail): each document depends on the one before it.
DESIGN_CHAIN = ["01_BRD.md", "02_PRD.md", "03_HLD.md", "04_LLD.md"]

# The course author's own text names their original files, so it is not ours to edit.
AUTHORS_TEXT = {"docs/03_HLD.md", "docs/04_LLD.md"}

# Every name a document had before it was numbered. A match means a reference was missed.
OLD_NAMES = [
    r"(?<![\d_])API_CONTRACT\.md",
    r"(?<![\d_])ARCHITECTURE\.md",
    r"Git_GitHub_Workflow_Guide",
    r"claude-setup-suggestions",
    r"01a_BRD",
    r"01b_PRD",
    r"02_HLD_Autonomous",
    r"03_LLD_Autonomous",
    r"01_PRD_BRD",
    r"Prompts_txt_zPBX",
    r"_adbX",
    r"_Lj7c",
    r"\b01[ab]\b",
]
TEXT_SUFFIXES = {".md", ".py", ".txt", ".toml", ".json", ".yaml", ".yml", ".sh", ".example"}


def _tracked_text_files() -> list[pathlib.Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available, so tracked files cannot be listed")
    paths = [ROOT / p for p in out if p]
    return [
        p
        for p in paths
        if p.is_file()
        and (p.suffix in TEXT_SUFFIXES or p.name in {"Makefile", "pre-commit"})
        and p.name != "uv.lock"
    ]


class TestNames:
    def test_every_file_in_docs_is_numbered_in_capitals_with_underscores(self):
        files = [p for p in DOCS.iterdir() if p.is_file()]

        assert [p.name for p in files if not DOC_NAME.match(p.name)] == []

    def test_the_numbers_are_unique_and_run_from_01_without_a_gap(self):
        numbers = sorted(
            int(DOC_NAME.match(p.name).group(1)) for p in DOCS.iterdir() if p.is_file()
        )

        assert numbers == list(range(1, len(numbers) + 1))

    def test_the_design_documents_come_first_in_dependency_order(self):
        names = sorted(p.name for p in DOCS.iterdir() if p.is_file())

        assert names[:4] == DESIGN_CHAIN

    @pytest.mark.parametrize(
        "name",
        ["01_BRD.md", "07_GIT_WORKFLOW.md", "09_PROMPT_COST.md", "12_NOTES.txt"],
    )
    def test_accepts(self, name: str):
        assert DOC_NAME.match(name)

    @pytest.mark.parametrize(
        "name",
        [
            "ARCHITECTURE.md",  # no number
            "1_BRD.md",  # not zero-padded: 10 would sort before 2
            "05_architecture.md",  # lower case
            "05-ARCHITECTURE.md",  # hyphen after the number
            "05_Git_GitHub_Workflow_Guide.md",  # mixed case
            "05_ARCHITECTURE.pdf",  # extension
        ],
    )
    def test_rejects(self, name: str):
        assert not DOC_NAME.match(name)

    def test_zero_padding_is_what_keeps_the_listing_in_reading_order(self):
        assert sorted(["10_X.md", "02_X.md", "09_X.md"]) == ["02_X.md", "09_X.md", "10_X.md"]
        assert sorted(["10_X.md", "2_X.md", "9_X.md"]) == ["10_X.md", "2_X.md", "9_X.md"]  # the bug


class TestNothingPointsAtAnOldName:
    def test_no_tracked_file_uses_a_name_a_document_had_before_numbering(self):
        patterns = [re.compile(p) for p in OLD_NAMES]
        offenders = []
        for path in _tracked_text_files():
            rel = path.relative_to(ROOT).as_posix()
            if rel in AUTHORS_TEXT or rel == "tests/unit/test_docs_folder.py":
                continue
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                offenders += [f"{rel}:{number}" for p in patterns if p.search(line)]

        assert offenders == []

    def test_every_relative_markdown_link_resolves_to_a_file(self):
        link = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
        broken = []
        for path in _tracked_text_files():
            rel = path.relative_to(ROOT).as_posix()
            if path.suffix != ".md" or rel in AUTHORS_TEXT:
                continue
            for target in link.findall(path.read_text(encoding="utf-8", errors="ignore")):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (path.parent / target).resolve().exists():
                    broken.append(f"{rel} -> {target}")

        assert broken == []
