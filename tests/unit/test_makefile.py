"""P1-4: the Makefile. `make` is not on every machine, so its structure is checked here."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
REQUIRED_TARGETS = {"setup", "backend", "test", "lint", "format"}


def _targets() -> dict[str, list[str]]:
    """Map each target to its recipe lines (the lines that follow it, indented with a tab)."""
    targets: dict[str, list[str]] = {}
    current = None
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        header = re.match(r"^([A-Za-z][\w-]*):(?!=)", line)
        if header:
            current = header.group(1)
            targets[current] = []
        elif line.startswith("\t") and current:
            targets[current].append(line.lstrip("\t"))
        elif line.strip() and not line.startswith("#") and not line.startswith(" "):
            current = None
    return targets


def test_every_required_target_exists():
    assert REQUIRED_TARGETS <= _targets().keys()


def test_every_target_is_declared_phony():
    phony = re.search(r"^\.PHONY:(.*)$", MAKEFILE.read_text(encoding="utf-8"), re.M)

    assert phony is not None
    assert set(_targets()) <= set(phony.group(1).split())


def test_recipes_are_indented_with_tabs_not_spaces():
    for number, line in enumerate(MAKEFILE.read_text(encoding="utf-8").splitlines(), start=1):
        assert not re.match(r"^ {2,}\S", line), f"Makefile line {number} is indented with spaces"


def test_the_file_uses_unix_line_endings_because_make_rejects_carriage_returns_in_recipes():
    assert b"\r\n" not in MAKEFILE.read_bytes()


def test_gitattributes_pins_the_makefile_to_unix_line_endings():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert re.search(r"^Makefile\s+text\s+eol=lf\s*$", attributes, re.M)


def test_test_target_runs_pytest_and_lint_target_runs_ruff():
    targets = _targets()

    assert any("uv run pytest" in line for line in targets["test"])
    assert any("uv run ruff check ." in line for line in targets["lint"])


def test_backend_target_serves_the_app_from_the_backend_folder():
    recipe = " ".join(_targets()["backend"])

    assert "uvicorn app.main:app" in recipe
    assert "--app-dir backend" in recipe


def test_setup_syncs_dependencies_and_creates_env_without_overwriting_an_existing_one():
    recipe = "\n".join(_targets()["setup"])

    assert "uv sync" in recipe
    assert ".env.example" in recipe and "'.env'" in recipe
    assert ".exists()" in recipe  # only copies when .env is missing


def test_every_recipe_goes_through_uv_so_it_runs_in_cmd_powershell_and_sh_alike():
    # `test`, `cp`, `rm` and `&&` are POSIX-shell features; PowerShell has none of them.
    for target, recipe in _targets().items():
        for line in recipe:
            command = line.lstrip("@-")
            assert command.startswith("uv "), f"{target}: {line!r} does not start with 'uv'"
            assert not any(token in command for token in ("&&", "||", "$(", "`", " rm ", " cp ")), (
                f"{target}: {line!r} uses shell-only syntax"
            )
