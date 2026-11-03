"""P1-14: the findings of the 2026-11-03 repository audit, each turned into a guard.

Every test here failed against the repository as audited, and each one stays as a regression
check. They cover configuration, hooks and ignore rules, and documents that had drifted.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8").replace("\r\n", "\n")


def _ignored(path: str) -> bool:
    """True when git would ignore the path, whether or not it is tracked."""
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=ROOT, capture_output=True
    )
    return result.returncode == 0


class TestTests:
    def test_the_client_fixture_imports_the_app_directly_so_a_broken_import_fails(self):
        conftest = _read("tests/conftest.py")

        assert "importorskip" not in conftest
        assert "until task P1-2" not in conftest


class TestFormatting:
    def test_ruff_is_told_to_leave_markdown_alone(self):
        config = tomllib.loads(_read("pyproject.toml"))["tool"]["ruff"]

        assert any(p.endswith(".md") for p in config.get("extend-exclude", []))

    @pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not available")
    def test_ruff_format_would_change_neither_claude_md_nor_the_authors_lld(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "--force-exclude",
                "CLAUDE.md",
                "docs/04_LLD.md",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr


class TestVersionAndIdentity:
    def test_the_version_is_the_same_in_pyproject_the_app_and_the_readme(self):
        pyproject = tomllib.loads(_read("pyproject.toml"))["project"]["version"]
        app = re.search(r'__version__ = "([^"]+)"', _read("backend/app/__init__.py")).group(1)
        readme = re.search(r"\*\*Version\*\*: (\S+)", _read("README.md")).group(1)

        assert pyproject == app == readme

    def test_the_package_description_uses_the_product_name(self):
        description = tomllib.loads(_read("pyproject.toml"))["project"]["description"]

        assert description.startswith("CloudDesk AI")

    def test_the_api_reports_the_product_name(self, client):
        title = client.get("/openapi.json").json()["info"]["title"]

        assert title == "CloudDesk AI API"

    @pytest.mark.parametrize(
        "name",
        [
            "CLAUDE.md",
            "PLAN.md",
            "TASKS.md",
            "MEMORY.md",
            "docs/05_ARCHITECTURE.md",
            "docs/07_GIT_WORKFLOW.md",
        ],
    )
    def test_the_main_documents_are_headed_with_the_product_name(self, name):
        heading = next(ln for ln in _read(name).splitlines() if ln.startswith("# "))

        assert "CloudDesk AI" in heading

    def test_the_unused_language_model_packages_are_explained_not_left_unexplained(self):
        text = _read("pyproject.toml")

        assert "installed up front" in text


class TestIgnoreRules:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.local",
            "data/support.db",
            "x.db",
            "terraform.tfvars",
            "infra/backend.hcl",
            ".claude/settings.local.json",
            "docs/plans/p2-1.md",
            "internal/Phase07/04_INTERVIEW_QNA.md",
        ],
    )
    def test_these_are_ignored(self, path):
        assert _ignored(path)

    @pytest.mark.parametrize(
        "path",
        [
            ".env.example",
            ".claude/settings.json",
            ".claude/hooks/pre-commit.sh",
            ".claude/agents/planner.md",
            "docs/plans/.gitkeep",
            "internal/Phase01/01_CODEBASE_EXPLAINED.md",
        ],
    )
    def test_these_are_not_ignored(self, path):
        assert not _ignored(path)


class TestHooks:
    def _sh(self):
        sh = shutil.which("sh")
        if sh is None:
            pytest.skip("sh is not available")
        return sh

    def test_the_claude_hook_lets_a_command_that_is_not_a_commit_straight_through(self):
        result = subprocess.run(
            [self._sh(), ".claude/hooks/pre-commit.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            input='{"tool_input": {"command": "ls -la"}}',
            timeout=60,
        )

        assert result.returncode == 0
        assert result.stderr == ""

    def test_the_claude_hook_blocks_with_exit_2_and_names_each_check(self):
        text = _read(".claude/hooks/pre-commit.sh")

        assert text.count("exit 2") == 2
        assert "ruff check" in text and "pytest" in text

    def test_the_git_hook_runs_the_stamp_script_and_skips_quietly_without_uv(self):
        text = _read(".githooks/pre-commit")

        assert "scripts/stamp_docs.py" in text
        assert "command -v uv" in text and "exit 0" in text

    @pytest.mark.parametrize("name", [".githooks/pre-commit", ".claude/hooks/pre-commit.sh"])
    def test_hook_scripts_have_unix_line_endings_because_sh_rejects_carriage_returns(self, name):
        assert b"\r" not in (ROOT / name).read_bytes() or "text eol=lf" in _read(".gitattributes")


class TestClaudeSettings:
    SETTINGS = json.loads(_read(".claude/settings.json"))

    def test_the_allow_list_cannot_delete_a_branch(self):
        allowed = self.SETTINGS["permissions"]["allow"]

        assert "Bash(git branch:*)" not in allowed

    def test_the_deny_list_covers_every_form_of_forced_push(self):
        denied = self.SETTINGS["permissions"]["deny"]

        for rule in (
            "Bash(git push --force:*)",
            "Bash(git push -f:*)",
            "Bash(git push --force-with-lease:*)",
        ):
            assert rule in denied


class TestSkills:
    def test_cost_report_uses_the_days_it_was_given_not_a_fixed_seven(self):
        text = _read(".claude/skills/cost-report/SKILL.md")

        assert "--days 7" not in text
        assert "--days $ARGUMENTS" in text

    def test_phase_docs_no_longer_tells_the_agent_to_edit_a_list_that_is_empty(self):
        assert "OWED" not in _read(".claude/skills/phase-docs/SKILL.md")

    def test_plan_files_have_a_naming_rule_and_a_stated_fate(self):
        skill = _read(".claude/skills/plan/SKILL.md")
        agent = _read(".claude/agents/planner.md")

        for text in (skill, agent):
            assert "<task-id>" in text or "p2-1.md" in text
        assert "not committed" in skill


class TestDocumentsHaveNotDrifted:
    STALE = [
        "Application code is not in the repo yet",
        "does not exist until task P1-2",
        "seven new skills",
        "squash-merge",
        "(4 of 67)",
        "State on 2026-10-31",
        "<DECIDE: probe result>",
        "compliance in PRD §11",
        "NFR-05 (offline operation)",
        "upstream NFR-07 and LLD",
    ]

    def test_no_document_still_says_something_that_stopped_being_true(self):
        offenders = []
        for rel in subprocess.run(
            ["git", "ls-files", "*.md", "*.py"], cwd=ROOT, capture_output=True, text=True
        ).stdout.split():
            if rel == "tests/unit/test_repo_hygiene.py":
                continue
            text = _read(rel)
            offenders += [f"{rel}: {p}" for p in self.STALE if p in text]

        assert offenders == []

    def test_the_git_workflow_has_a_real_title_so_the_stamp_is_not_under_contents(self):
        first = next(ln for ln in _read("docs/07_GIT_WORKFLOW.md").splitlines() if ln.strip())

        assert first.startswith("# ")
        assert "# Contents\n\n_Last updated" not in _read("docs/07_GIT_WORKFLOW.md")

    def test_the_workflow_guide_lists_the_branch_prefixes_the_tracker_uses(self):
        guide = _read("docs/07_GIT_WORKFLOW.md")

        for prefix in ("docs/", "chore/"):
            assert prefix in guide

    def test_the_phase_documentation_spec_headings_are_all_the_same_level(self):
        headings = re.findall(r"^(#{1,2}) \d+\. ", _read("docs/09_PHASE_DOCUMENTATION.md"), re.M)

        assert set(headings) == {"#"}

    def test_the_phase_documentation_spec_records_that_the_qna_file_is_git_ignored(self):
        assert "git-ignored" in _read("docs/09_PHASE_DOCUMENTATION.md")

    def test_the_claude_md_commands_and_layout_are_complete(self):
        text = _read("CLAUDE.md")

        assert "make format" in text
        assert "check_phase_docs.py" in text
        assert "docs/adr/" in text

    def test_the_setup_notes_do_not_state_a_line_count_that_will_drift(self):
        assert not re.search(
            r"\| `CLAUDE.md` \| repository root \| \d+ \|", _read("docs/08_CLAUDE_SETUP.md")
        )

    def test_phase_1_documents_say_their_test_counts_are_a_snapshot(self):
        text = _read("internal/Phase01/01_CODEBASE_EXPLAINED.md")

        assert "whole suite today" not in text
        assert "P1-5 to P1-10" not in text

    def test_the_setup_notes_no_longer_say_there_is_no_adr_folder(self):
        assert "no ADR folder" not in _read("docs/08_CLAUDE_SETUP.md")


class TestPlansAgreeWithTheUpstreamDocuments:
    def test_every_requirement_id_we_cite_exists_in_the_upstream_prd(self):
        prd = _read("docs/02_PRD.md")
        known = set(re.findall(r"\b(?:FR|NFR)-\d+\b", prd))
        cited = {}
        for rel in subprocess.run(
            ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True
        ).stdout.split():
            if rel.startswith(("docs/01_", "docs/02_", "docs/03_", "docs/04_")):
                continue
            for ident in re.findall(r"\b(?:FR|NFR)-\d+\b", _read(rel)):
                cited.setdefault(ident, rel)

        assert {k: v for k, v in cited.items() if k not in known} == {}

    def test_tenancy_cites_the_multi_tenancy_requirement_not_the_security_one(self):
        assert "FR-42" in _read("docs/adr/0001-tenant-id-on-every-table.md")
        assert "FR-42" in _read("MEMORY.md")

    def test_the_traceability_table_leaves_no_upstream_must_requirement_unmentioned(self):
        plan = _read("PLAN.md")

        for ident in ("FR-36", "FR-41", "NFR-05", "NFR-06", "NFR-13"):
            assert ident in plan

    def test_kubernetes_is_not_planned_as_built_while_it_is_undecided(self):
        assert "deployment/kubernetes" not in _read("PLAN.md")
        layout = next(ln for ln in _read("CLAUDE.md").splitlines() if ln.startswith("deployment/"))
        assert "kubernetes/" not in layout or "D5" in layout

    def test_the_run_route_is_in_the_same_file_in_the_spec_and_in_the_plan(self):
        assert "api/workflow.py::run_workflow" in _read("CLAUDE.md")
        assert "api/tickets.py::run_workflow" not in _read("CLAUDE.md")

    def test_the_spec_lists_the_tenants_table_beside_the_sixteen(self):
        assert "plus `tenants`" in _read("CLAUDE.md").split("## 6. Data model")[1].split("## 7.")[0]

    def test_the_first_harness_task_no_longer_describes_a_skipping_fixture_as_current(self):
        task = _read("TASKS.md").split("**P1-3 · Offline pytest harness**")[1].split("**P1-4")[0]

        assert "P1-14" in task
