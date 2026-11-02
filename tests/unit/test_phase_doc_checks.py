"""P1-8: completion checks for phase documentation, and the helpers that keep them honest.

What these can and cannot show. They prove the four files exist and are not empty, that every file
path a document cites exists, and that each Mermaid block is structurally sound. They do NOT prove a
document describes the code accurately, and they do NOT render Mermaid: that needs a human
review and a renderer, and neither is available offline.
"""

import pathlib
import subprocess

import pytest

from scripts.check_phase_docs import (
    cited_paths,
    finished_phases,
    mermaid_problems,
    missing_paths,
    phase_statuses,
    required_documents,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTERNAL = ROOT / "internal"
PLAN = ROOT / "PLAN.md"
MIN_BYTES = 200

# Phases whose four documents are still to be written. Remove a phase from this set when they land:
# test_the_owed_list_names_only_phases_that_are_still_owed fails if you forget.
OWED: set[int] = set()


def _qna_is_git_ignored() -> bool:
    """A git-ignored Q&A file is absent from a clean clone, so it cannot be required there."""
    try:
        run = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", "internal/Phase01/04_INTERVIEW_QNA.md"],
            cwd=ROOT,
        )
    except OSError:
        return False
    return run.returncode == 0


def _required(phase: int) -> list[pathlib.Path]:
    return [ROOT / p for p in required_documents(phase, qna_required=not _qna_is_git_ignored())]


def _finished_phases() -> set[int]:
    return finished_phases(phase_statuses(PLAN.read_text(encoding="utf-8")))


def _phase_documents() -> list[pathlib.Path]:
    return sorted(INTERNAL.rglob("*.md")) if INTERNAL.exists() else []


class TestCitedPaths:
    def test_finds_a_repository_path_in_backticks(self):
        assert cited_paths("It lives in `backend/app/main.py` today.") == [
            (1, "backend/app/main.py")
        ]

    def test_ignores_a_path_that_is_not_in_backticks(self):
        assert cited_paths("See backend/app/main.py for details.") == []

    def test_keeps_the_line_number_it_was_found_on(self):
        assert cited_paths("one\ntwo `a/b.py`\nthree") == [(2, "a/b.py")]

    def test_ignores_everything_inside_a_fenced_block(self):
        assert cited_paths("```text\nproject/\n  `rag/chunking.py`\n```\n") == []

    @pytest.mark.parametrize(
        "token",
        [
            "https://example.com/a/b.md",
            "/etc/hosts.conf",
            "~/.claude/settings.json",
            "C:\\Users\\me\\file.py",
            "$HOME/file.py",
        ],
    )
    def test_ignores_external_and_absolute_paths(self, token: str):
        assert cited_paths(f"See `{token}` here.") == []

    @pytest.mark.parametrize(
        "token",
        [
            "internal/<name>/x.md",
            "tests/*.py",
            "Phase<N>_explained.md",
            "src/{a,b}.py",
            "a/.../b.py",
        ],
    )
    def test_ignores_placeholders_and_globs(self, token: str):
        assert cited_paths(f"Pattern `{token}` only.") == []

    @pytest.mark.parametrize(
        "token", [".env", "data/support.db", ".venv/Scripts/python.exe", "node_modules/x.js"]
    )
    def test_ignores_local_only_files_that_are_never_in_a_clone(self, token: str):
        assert cited_paths(f"Local file `{token}`.") == []

    @pytest.mark.parametrize(
        "marker", ["planned", "future", "removed", "historical", "proposed", "not yet"]
    )
    def test_ignores_a_line_that_says_the_file_is_not_current(self, marker: str):
        assert cited_paths(f"The `rag/retriever.py` file is {marker}.") == []

    def test_strips_a_line_number_or_anchor_from_the_path(self):
        assert cited_paths("At `backend/app/main.py:42` and `docs/a.md#intro`.") == [
            (1, "backend/app/main.py"),
            (1, "docs/a.md"),
        ]

    def test_ignores_commands_and_flags_because_they_contain_spaces_or_a_dash(self):
        assert cited_paths("Run `uv run pytest -q` or `--bare`.") == []

    def test_a_bare_file_name_with_a_known_extension_is_a_path(self):
        assert cited_paths("Edit `conftest.py` first.") == [(1, "conftest.py")]

    def test_a_slash_word_without_a_file_extension_is_not_a_path(self):
        assert cited_paths("The `request_id/workflow_id` pair and `backend/app/api`.") == []

    def test_a_trailing_slash_marks_a_directory(self):
        assert cited_paths("The `backend/app/` folder.") == [(1, "backend/app/")]


class TestMissingPaths:
    def test_a_path_that_exists_is_not_reported(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b.py").write_text("x", encoding="utf-8")

        assert missing_paths("`a/b.py`", tmp_path) == []

    def test_a_path_that_does_not_exist_is_reported_with_its_line(self, tmp_path):
        assert missing_paths("ok\n`a/ghost.py`", tmp_path) == [(2, "a/ghost.py")]

    def test_a_directory_is_checked_as_a_directory(self, tmp_path):
        (tmp_path / "a").mkdir()

        assert missing_paths("`a/` and `b/`", tmp_path) == [(1, "b/")]

    def test_a_bare_file_name_is_found_anywhere_in_the_tree(self, tmp_path):
        (tmp_path / "deep" / "er").mkdir(parents=True)
        (tmp_path / "deep" / "er" / "conftest.py").write_text("x", encoding="utf-8")

        assert missing_paths("`conftest.py` and `ghost.py`", tmp_path) == [(1, "ghost.py")]

    def test_a_bare_name_that_exists_only_inside_the_virtualenv_does_not_count(self, tmp_path):
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        (tmp_path / ".venv" / "lib" / "only_here.py").write_text("x", encoding="utf-8")

        assert missing_paths("`only_here.py`", tmp_path) == [(1, "only_here.py")]


class TestMermaid:
    def _block(self, body: str) -> str:
        return f"text\n\n```mermaid\n{body}\n```\n"

    @pytest.mark.parametrize(
        "body",
        [
            "flowchart TD\n  A --> B",
            "graph LR\n  A --> B",
            "sequenceDiagram\n  A->>B: hi",
            "classDiagram\n  class A",
            "stateDiagram-v2\n  [*] --> A",
            "erDiagram\n  A ||--o{ B : has",
            "%% a comment first\nflowchart TD\n  A --> B",
            "---\ntitle: T\n---\nflowchart TD\n  A --> B",
            "flowchart TD\n  subgraph S\n    A\n  end",
        ],
    )
    def test_accepts_a_sound_block(self, body: str):
        assert mermaid_problems(self._block(body)) == []

    def test_a_document_with_no_diagram_has_nothing_to_flag(self):
        assert mermaid_problems("# Title\n\nJust text.\n") == []

    def test_flags_an_unrecognised_diagram_type(self):
        assert any(
            "unrecognised" in p for p in mermaid_problems(self._block("flowchrt TD\n  A --> B"))
        )

    def test_flags_an_empty_block(self):
        assert any("empty" in p for p in mermaid_problems(self._block("%% only a comment")))

    def test_flags_a_block_that_is_never_closed(self):
        assert any(
            "never closed" in p for p in mermaid_problems("```mermaid\nflowchart TD\n  A --> B\n")
        )

    def test_flags_a_subgraph_with_no_end(self):
        problems = mermaid_problems(self._block("flowchart TD\n  subgraph S\n    A"))

        assert any("subgraph" in p for p in problems)

    def test_does_not_look_inside_other_fenced_blocks(self):
        assert mermaid_problems("```python\nflowchrt = 1\n```\n") == []


class TestPhaseStatuses:
    def test_reads_the_phase_table(self):
        plan = "| 1 | Runtime skeleton | validated locally |\n| 2 | Persistence | not started |\n"

        assert phase_statuses(plan) == {1: "validated locally", 2: "not started"}

    def test_the_real_plan_lists_all_fourteen_phases(self):
        statuses = phase_statuses(PLAN.read_text(encoding="utf-8"))

        assert sorted(statuses) == list(range(1, 15))


class TestFinishedPhases:
    """Documents grow during a phase, so they are demanded only once a phase is finished."""

    def test_only_implemented_and_validated_phases_are_finished(self):
        statuses = {1: "validated locally", 2: "in progress", 3: "not started", 4: "implemented"}

        assert finished_phases(statuses) == {1, 4}

    def test_a_phase_in_progress_is_not_required_to_have_all_four_documents_yet(self):
        assert 2 not in finished_phases({2: "in progress"})

    def test_a_phase_not_started_is_never_finished(self):
        assert finished_phases({5: "not started"}) == set()


class TestRequiredDocuments:
    def test_a_phase_has_the_four_documents_the_spec_defines(self):
        assert required_documents(3) == [
            "internal/Phase03/01_CODEBASE_EXPLAINED.md",
            "internal/Phase03/02_DESIGN_EVOLUTION.md",
            "internal/Phase03/03_INFRA_EVOLUTION.md",
            "internal/Phase03/04_INTERVIEW_QNA.md",
        ]

    def test_the_qna_document_can_be_left_out_when_it_is_private(self):
        names = required_documents(3, qna_required=False)

        assert len(names) == 3
        assert not any("interview_qna" in n for n in names)


class TestCompletion:
    def test_every_finished_phase_has_its_documents_or_is_owed(self):
        problems = []
        for phase in sorted(_finished_phases() - OWED):
            for path in _required(phase):
                if not path.exists():
                    problems.append(f"phase {phase}: missing {path.relative_to(ROOT).as_posix()}")
                elif path.stat().st_size < MIN_BYTES:
                    problems.append(f"phase {phase}: {path.name} is under {MIN_BYTES} bytes")

        assert problems == []

    def test_the_owed_list_names_only_phases_that_are_still_owed(self):
        finished = [
            n
            for n in sorted(OWED)
            if all(p.exists() and p.stat().st_size >= MIN_BYTES for p in _required(n))
        ]

        assert finished == [], (
            f"phase(s) {finished} now have their documents: remove them from OWED"
        )

    def test_only_a_finished_phase_can_be_owed(self):
        assert OWED <= _finished_phases()

    def test_every_phase_document_cites_only_paths_that_exist(self):
        problems = [
            f"{doc.relative_to(ROOT).as_posix()}:{line}: `{path}`"
            for doc in _phase_documents()
            for line, path in missing_paths(doc.read_text(encoding="utf-8"), ROOT)
        ]

        assert problems == []

    def test_every_mermaid_block_in_a_phase_document_is_structurally_sound(self):
        problems = [
            f"{doc.relative_to(ROOT).as_posix()}: {p}"
            for doc in _phase_documents()
            for p in mermaid_problems(doc.read_text(encoding="utf-8"))
        ]

        assert problems == []


class TestInternalFolderVisibility:
    """The repository is public: the Q&A file is private; the other three documents are not."""

    def _ignored(self, path: str) -> bool:
        return (
            subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=ROOT).returncode
            == 0
        )

    def test_the_interview_qna_file_is_git_ignored(self):
        assert self._ignored("internal/Phase01/04_INTERVIEW_QNA.md")
        assert self._ignored(
            "internal/Phase12/04_INTERVIEW_QNA.md"
        )  # every phase, not just the first

    @pytest.mark.parametrize(
        "path",
        [
            "internal/Phase01/01_CODEBASE_EXPLAINED.md",
            "internal/Phase01/02_DESIGN_EVOLUTION.md",
            "internal/Phase01/03_INFRA_EVOLUTION.md",
        ],
    )
    def test_the_other_three_documents_are_not_ignored_so_they_can_be_committed(self, path: str):
        assert not self._ignored(path)

    def test_no_interview_qna_file_is_already_tracked(self):
        tracked = subprocess.run(
            ["git", "ls-files", "internal"], cwd=ROOT, capture_output=True, text=True
        ).stdout.split()

        assert [p for p in tracked if p.endswith("04_INTERVIEW_QNA.md")] == []
