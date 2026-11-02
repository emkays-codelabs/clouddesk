#!/bin/sh
# PreToolUse hook on the Bash tool: before Claude runs `git commit`, run lint and the tests.
#
# Exit 0 lets the command through. Exit 2 blocks it and shows stderr to Claude.
# It fails open: a missing tool never blocks a commit.
#
# The payload is JSON on stdin and jq is not installed here, so the command is matched on the raw text.
# A command that merely mentions "git commit" also triggers the checks. That costs a few seconds and
# never blocks anything that passes, so it is the safe direction to be wrong in.
#
# Only Python exists so far. When frontend/ lands (Phase 12), add `npm run lint` and `npm run test` here.
payload=$(cat)

case "$payload" in
    *"git commit"*) ;;
    *) exit 0 ;;
esac

if ! command -v uv >/dev/null 2>&1; then
    echo "pre-commit hook: uv not found, skipping lint and tests" >&2
    exit 0
fi

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$root" || exit 0

# The command may stage and commit in one go (`git add ... && git commit`), in which case nothing is
# staged yet when this hook runs. Lint the whole tree: ruff is fast and the result is the same.
if ! out=$(uv run --quiet ruff check . 2>&1); then
    echo "Commit blocked: ruff check failed." >&2
    echo "$out" | tail -25 >&2
    exit 2
fi

if ! out=$(uv run --quiet pytest -q -x 2>&1); then
    echo "Commit blocked: tests failed." >&2
    echo "$out" | tail -25 >&2
    exit 2
fi

exit 0
