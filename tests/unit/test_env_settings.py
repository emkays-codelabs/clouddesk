"""The variable list in CLAUDE.md section 10.1 and the Settings fields cannot drift apart.

There is no committed .env template: the git-ignored .env is created by hand, so section 10.1
is the one list a person copies from. This test replaces the old .env.example coverage test (the
template was removed on 2026-11-27 at the owner's request).
"""

import re
import subprocess
from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").replace("\r\n", "\n")


def _section_10_1() -> str:
    body = CLAUDE.split("### 10.1 ")[1].split("### 10.2")[0]
    return body.split("```text")[1].split("```")[0]


def _listed_variables() -> set[str]:
    return set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", _section_10_1()))


def _fields() -> set[str]:
    return {name.upper() for name in Settings.model_fields}


def test_section_10_1_names_every_settings_field():
    assert _fields() - _listed_variables() == set()


def test_section_10_1_names_nothing_the_application_does_not_read():
    assert _listed_variables() - _fields() == set()


def test_llm_base_url_is_listed_exactly_once_in_the_spec():
    assert CLAUDE.count("LLM_BASE_URL") == 1


def test_no_environment_file_is_tracked_by_git():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    present = [p for p in tracked if (ROOT / p).exists()]  # a deletion not yet committed is fine

    assert [p for p in present if Path(p).name == ".env" or Path(p).name.startswith(".env.")] == []


def test_the_environment_file_is_git_ignored():
    for name in (".env", ".env.local", ".env.production"):
        result = subprocess.run(["git", "check-ignore", "-q", name], cwd=ROOT)

        assert result.returncode == 0, f"{name} must be ignored"


def test_the_spec_lists_names_only_never_a_secret_value():
    section = _section_10_1()

    assert not re.search(r"(^|[\s=])sk-", section) and "password" not in section.lower()


def test_compose_only_variables_are_not_settings_fields():
    assert {"BACKEND_PORT", "FRONTEND_PORT"} & _fields() == set()
