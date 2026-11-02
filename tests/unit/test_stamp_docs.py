"""P1-5: the pre-commit stamper that records when each document last changed."""

import re
import types
from datetime import UTC, datetime, timedelta, timezone

import pytest

from scripts import stamp_docs
from scripts.stamp_docs import STAMPED, find_stamp, stamp_files, stamp_text

NOW = datetime(2026, 11, 2, 14, 35, tzinfo=timezone(timedelta(hours=5, minutes=30)))
LINE = "_Last updated: 2026-11-02 14:35 +0530_"


class TestStampText:
    def test_inserts_the_stamp_after_the_first_heading(self):
        out = stamp_text("# Title\n\nBody.\n", NOW)

        assert out == f"# Title\n\n{LINE}\n\nBody.\n"

    def test_replaces_an_existing_stamp_in_place(self):
        before = "# Title\n\n_Last updated: 2020-01-01 00:00 +0000_\n\nBody.\n"

        out = stamp_text(before, NOW)

        assert out == f"# Title\n\n{LINE}\n\nBody.\n"
        assert "2020-01-01" not in out

    def test_running_twice_changes_nothing_more(self):
        once = stamp_text("# Title\n\nBody.\n", NOW)

        assert stamp_text(once, NOW) == once

    def test_a_moved_or_duplicated_stamp_collapses_to_exactly_one(self):
        messy = (
            "# Title\n\n_Last updated: 2020-01-01 00:00 +0000_\n\nBody.\n\n"
            "_Last updated: 2019-01-01 00:00 +0000_\n"
        )

        out = stamp_text(messy, NOW)

        assert out.count("_Last updated:") == 1
        assert out.splitlines()[2] == LINE

    def test_a_file_with_no_heading_is_stamped_at_the_top(self):
        out = stamp_text("Just prose.\n", NOW)

        assert out == f"{LINE}\n\nJust prose.\n"

    def test_the_stamp_follows_yaml_frontmatter_and_its_heading(self):
        src = "---\nname: a-skill\n---\n\n# A skill\n\nBody.\n"

        out = stamp_text(src, NOW)

        assert out == f"---\nname: a-skill\n---\n\n# A skill\n\n{LINE}\n\nBody.\n"

    def test_a_hash_inside_a_code_fence_is_not_mistaken_for_the_heading(self):
        src = "```bash\n# not a heading\n```\n\n# Real heading\n\nBody.\n"

        out = stamp_text(src, NOW)

        assert out.index(LINE) > out.index("# Real heading")

    def test_the_body_is_left_byte_identical_apart_from_the_stamp(self):
        body = "# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```py\nx = 1  # keep\n```\n"

        out = stamp_text(body, NOW)

        assert out.replace(f"{LINE}\n\n", "") == body

    def test_a_file_without_a_trailing_newline_gains_one(self):
        assert stamp_text("# T\n\nBody.", NOW).endswith("\n")

    @pytest.mark.parametrize("eol", ["\n", "\r\n"], ids=["lf", "crlf"])
    def test_the_file_keeps_its_own_line_endings(self, eol: str):
        out = stamp_text(f"# T{eol}{eol}Body.{eol}", NOW)

        assert eol.join(out.split(eol)) == out
        assert ("\r\n" in out) == (eol == "\r\n")


class TestFindStamp:
    def test_reads_back_the_time_it_wrote(self):
        assert find_stamp(stamp_text("# T\n", NOW)) == LINE

    def test_returns_none_when_there_is_no_stamp(self):
        assert find_stamp("# T\n\nBody.\n") is None


class TestStampedList:
    def test_the_project_documents_are_listed(self):
        assert "CLAUDE.md" in STAMPED
        assert "TASKS.md" in STAMPED
        assert ".claude/skills/clouddesk-support/SKILL.md" in STAMPED

    def test_the_upstream_authors_documents_are_never_stamped(self):
        # They carry their own version date; overwriting it would misreport the author.
        # docs/01 to docs/04 are the BRD, PRD, HLD and LLD. The project's own documents start at 05.
        assert not [p for p in STAMPED if re.match(r"docs/0[1-4]_", p)]

    def test_every_listed_file_exists(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        assert [p for p in STAMPED if not (root / p).exists()] == []

    def test_the_utc_case_formats_without_crashing(self):
        assert "+0000" in stamp_text("# T\n", datetime(2026, 1, 1, tzinfo=UTC))


class TestStampFiles:
    """stamp_files must honour STAMPED, not just contain the right names."""

    def _tree(self, tmp_path):
        (tmp_path / "docs").mkdir()
        listed = tmp_path / "CLAUDE.md"
        listed.write_text("# T\n\nBody.\n", encoding="utf-8")
        unlisted = tmp_path / "docs" / "03_HLD.md"
        unlisted.write_text("# HLD\n\n| Date | 31 October 2026 |\n", encoding="utf-8")
        return listed, unlisted

    def test_a_listed_file_is_stamped(self, tmp_path):
        listed, _ = self._tree(tmp_path)

        assert stamp_files(["CLAUDE.md"], tmp_path, NOW) == ["CLAUDE.md"]
        assert LINE in listed.read_text(encoding="utf-8")

    def test_an_unlisted_file_is_left_byte_identical(self, tmp_path):
        _, unlisted = self._tree(tmp_path)
        rel = "docs/03_HLD.md"
        before = unlisted.read_bytes()

        # The author's own version date must survive, so the guard is load-bearing, not decoration.
        assert stamp_files([rel], tmp_path, NOW) == []
        assert unlisted.read_bytes() == before

    def test_a_missing_path_is_skipped_rather_than_raising(self, tmp_path):
        assert stamp_files(["CLAUDE.md"], tmp_path, NOW) == []

    def test_an_already_current_file_is_not_rewritten(self, tmp_path):
        listed, _ = self._tree(tmp_path)
        stamp_files(["CLAUDE.md"], tmp_path, NOW)
        before = listed.read_bytes()

        assert stamp_files(["CLAUDE.md"], tmp_path, NOW) == []
        assert listed.read_bytes() == before


class TestWhichStagedFilesAreConsidered:
    """A document that is renamed and edited in the same commit is Renamed, not Modified, to git."""

    def test_a_renamed_file_is_asked_for_so_its_edit_is_still_stamped(self, monkeypatch):
        seen = {}

        def fake_run(command, **_):
            seen["command"] = command
            return types.SimpleNamespace(stdout="")

        monkeypatch.setattr(stamp_docs.subprocess, "run", fake_run)

        assert stamp_docs.main([]) == 0
        flag = next(a for a in seen["command"] if a.startswith("--diff-filter="))
        assert "R" in flag, f"{flag} would skip a renamed file"
