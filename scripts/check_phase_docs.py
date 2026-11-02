"""Checks for the phase documents that docs/09_PHASE_DOCUMENTATION.md requires.

What these establish: a cited file path exists, a Mermaid block is structurally sound, and a phase's
four documents are present. What they do not establish: that a document describes the code
accurately, or that a diagram renders. Nothing here is an online dependency.
"""

from __future__ import annotations

import os
import pathlib
import re

FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_RE = re.compile(r"`([^`\n]+)`")
PHASE_ROW_RE = re.compile(
    r"^\| (\d+) \| [^|]+ \| (not started|in progress|implemented|validated locally) \|$", re.M
)

# A line that says the file is not current is allowed to name a file that does not exist.
NOT_CURRENT = ("planned", "future", "removed", "historical", "proposed", "not yet")

# Files a clean clone never has, so a document may cite them freely.
LOCAL_ONLY_EXACT = {".env", ".claude/settings.local.json"}
LOCAL_ONLY_PREFIXES = (".venv", "node_modules", "data/")

EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".sql", ".sh", ".ini", ".cfg",
    ".ts", ".tsx", ".js", ".css", ".hcl", ".tf", ".tfvars", ".lock", ".example",
}  # fmt: skip
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}

MERMAID_DECLARATIONS = {
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
    "erDiagram", "journey", "gantt", "pie", "mindmap", "timeline", "gitGraph", "requirementDiagram",
    "quadrantChart", "sankey-beta", "xychart-beta", "block-beta", "C4Context",
}  # fmt: skip

# The four documents docs/09_PHASE_DOCUMENTATION.md defines, in each phase folder internal/PhaseNN/.
# The number keeps them in reading order; the last one is the private interview preparation.
DOCUMENTS = [
    "01_CODEBASE_EXPLAINED.md",
    "02_DESIGN_EVOLUTION.md",
    "03_INFRA_EVOLUTION.md",
    "04_INTERVIEW_QNA.md",
]
PRIVATE_DOCUMENT = "04_INTERVIEW_QNA.md"


def required_documents(phase: int, qna_required: bool = True) -> list[str]:
    """The paths, relative to the repository root, of the documents a phase owes."""
    return [
        f"internal/Phase{phase:02d}/{name}"
        for name in DOCUMENTS
        if qna_required or name != PRIVATE_DOCUMENT
    ]


def phase_statuses(plan_text: str) -> dict[int, str]:
    """`{phase number: status}` from the Build phases table in PLAN.md."""
    return {int(n): status for n, status in PHASE_ROW_RE.findall(plan_text)}


FINISHED = {"implemented", "validated locally"}


def finished_phases(statuses: dict[int, str]) -> set[int]:
    """The phases whose four documents are due: finished ones, not those still in progress.

    Documents grow during a phase (the spec's section 7, Step 4), so a phase in progress may have
    only some of them. They are required once the phase is implemented.
    """
    return {n for n, status in statuses.items() if status in FINISHED}


def _as_path(token: str) -> str | None:
    """The repository path a backticked token names, or None if it is not one."""
    t = token.strip()
    if not t or " " in t:
        return None
    if t.startswith(("http://", "https://", "/", "~", "$", "-")) or re.match(r"^[A-Za-z]:[\\/]", t):
        return None
    if any(c in t for c in "<>*{}|\\") or "..." in t:
        return None
    t = re.split(r"[:#]", t, maxsplit=1)[0].rstrip(".,;)")
    if not t:
        return None
    if t in LOCAL_ONLY_EXACT or t.startswith(LOCAL_ONLY_PREFIXES):
        return None
    if t.endswith("/"):
        return t
    if pathlib.PurePosixPath(t).suffix in EXTENSIONS:
        return t
    return None


def cited_paths(markdown: str) -> list[tuple[int, str]]:
    """`(line number, path)` for each repository path a document cites in backticks.

    Fenced blocks are skipped, because a directory tree may legitimately show planned files. A line
    that says planned, future, removed, historical, proposed or not yet is skipped for the same
    reason.
    """
    found: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(markdown.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or any(marker in line.lower() for marker in NOT_CURRENT):
            continue
        for token in INLINE_RE.findall(line):
            path = _as_path(token)
            if path:
                found.append((number, path))
    return found


def _exists(root: pathlib.Path, path: str) -> bool:
    if path.endswith("/"):
        return (root / path.rstrip("/")).is_dir()
    if "/" in path:
        return (root / path).exists()
    # A bare file name: it counts if a file with that name is anywhere in the tree.
    for _, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        if path in files:
            return True
    return False


def missing_paths(markdown: str, root: pathlib.Path) -> list[tuple[int, str]]:
    """The cited paths that do not exist under `root`."""
    return [(n, p) for n, p in cited_paths(markdown) if not _exists(root, p)]


def mermaid_problems(markdown: str) -> list[str]:
    """Structural problems in a document's Mermaid blocks: a syntax check, not a render."""
    blocks: list[tuple[int, str, list[str]]] = []
    current: tuple[int, str, list[str]] | None = None
    for number, line in enumerate(markdown.splitlines(), 1):
        if current is None:
            opening = re.match(r"^\s*(```|~~~)\s*mermaid\s*$", line)
            if opening:
                current = (number, opening.group(1), [])
        elif line.strip().startswith(current[1]):
            blocks.append(current)
            current = None
        else:
            current[2].append(line)

    problems: list[str] = []
    if current is not None:
        problems.append(f"line {current[0]}: mermaid block is never closed")

    for start, _, body in blocks:
        lines = [ln.strip() for ln in body if ln.strip() and not ln.strip().startswith("%%")]
        if lines and lines[0] == "---":  # optional front matter, such as a title
            closing = next((i for i, ln in enumerate(lines[1:], 1) if ln == "---"), None)
            lines = lines[closing + 1 :] if closing is not None else []
        if not lines:
            problems.append(f"line {start}: empty mermaid block")
            continue
        kind = lines[0].split()[0]
        if kind not in MERMAID_DECLARATIONS:
            problems.append(f"line {start}: unrecognised diagram type {kind!r}")
        if kind in {"flowchart", "graph"}:
            opened = sum(1 for ln in lines if ln.startswith("subgraph"))
            closed = sum(1 for ln in lines if ln == "end")
            if opened != closed:
                problems.append(f"line {start}: {opened} subgraph but {closed} end")
    return problems
