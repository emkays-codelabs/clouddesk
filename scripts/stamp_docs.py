"""Record in each document when it last changed, from the pre-commit hook.

Git already knows this exactly (`git log -1 --format=%cI -- <file>`), so the stamp is a convenience
for anyone reading the file on its own, outside a clone. The hook stamps only the files staged
in the commit, so a document's line always matches the commit that last touched it.

The upstream author's documents in `docs/01a`, `01b`, `02` and `03` are deliberately absent from
STAMPED: they carry their own version date, and overwriting it would misreport their author.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
from datetime import datetime

PREFIX = "_Last updated: "
STAMP_RE = re.compile(rf"^{re.escape(PREFIX)}.*_$", re.M)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^# \S")

# The project's own documents. Anything not listed here is left alone.
STAMPED = [
    "CLAUDE.md",
    "PLAN.md",
    "TASKS.md",
    "MEMORY.md",
    "README.md",
    "docs/API_CONTRACT.md",
    "docs/ARCHITECTURE.md",
    "docs/Git_GitHub_Workflow_Guide.md",
    ".claude/skills/clouddesk-support/SKILL.md",
]


def find_stamp(text: str) -> str | None:
    """The stamp line currently in the text, or None."""
    match = STAMP_RE.search(text)
    return match.group(0) if match else None


def _insert_at(lines: list[str]) -> int:
    """The line index the stamp belongs on: just after the first real H1, else the very top."""
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        # A "# " inside a fenced block is a shell comment, not a heading.
        if not in_fence and HEADING_RE.match(line):
            return i + 1
    return 0


def stamp_text(text: str, now: datetime) -> str:
    """Return the text carrying exactly one stamp, in the canonical place."""
    newline = "\r\n" if "\r\n" in text else "\n"
    line = f"{PREFIX}{now.strftime('%Y-%m-%d %H:%M %z')}_"

    # Drop every existing stamp first, so a moved or duplicated one collapses to one.
    body = [ln for ln in text.replace("\r\n", "\n").split("\n") if not STAMP_RE.match(ln)]
    while body and body[-1] == "":
        body.pop()

    at = _insert_at(body)
    before, after = body[:at], body[at:]
    while before and before[-1] == "":
        before.pop()
    while after and after[0] == "":
        after.pop(0)

    parts = ([*before, ""] if before else []) + [line] + (["", *after] if after else [])
    return newline.join(parts) + newline


def stamp_files(paths: list[str], root: pathlib.Path, now: datetime) -> list[str]:
    """Stamp each path that is in STAMPED. Returns the paths actually rewritten."""
    changed = []
    for rel in paths:
        if rel not in STAMPED:
            continue
        path = root / rel
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        updated = stamp_text(original, now)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed.append(rel)
    return changed


def main(argv: list[str]) -> int:
    root = pathlib.Path(__file__).resolve().parents[1]
    paths = argv or [
        p
        for p in subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if p
    ]
    changed = stamp_files(paths, root, datetime.now().astimezone())
    for rel in changed:
        # Re-stage, so the stamp is part of the commit that caused it.
        subprocess.run(["git", "add", "--", rel], cwd=root, check=True)
        print(f"stamped {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
