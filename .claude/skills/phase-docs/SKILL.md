---
name: phase-docs
description: Write the four mandatory documents for a finished phase: codebase explanation, system design evolution, infrastructure evolution, and interview Q&A. Use when a phase's exit criteria pass.
context: fork
agent: general-purpose
background: false
disable-model-invocation: true
argument-hint: "[phase number, e.g. 1]"
---

Write the four documents for phase $ARGUMENTS.

1. Read `docs/09_PHASE_DOCUMENTATION.md` in full. It is the specification: follow its structure, its
   quality standards (section 8) and its definition of done (section 9).
2. Find what the phase changed. Take its rows from `TASKS.md`; each names a branch. For each branch find
   its merge commit with `git log --merges --first-parent --grep "<branch>" --format="%h %s"` and read
   what it changed with `git diff <hash>^1 <hash> --stat`. Then read the code. Never credit this phase
   with a later phase's work.
3. Document only what exists. Mark each item implemented, partial, planned, or a future recommendation.
   Cite file paths in backticks: a test fails on any cited path that does not exist. On a line that
   names a planned, removed or historical file, use that word.
4. Write these files, creating the folders if missing. If one exists, update it in place and keep what is
   still true:
   - `internal/Phase<N>/01_CODEBASE_EXPLAINED.md`
   - `internal/Phase<N>/02_DESIGN_EVOLUTION.md`
   - `internal/Phase<N>/03_INFRA_EVOLUTION.md`
   - `internal/Phase<N>/04_INTERVIEW_QNA.md`
5. Claim a test passed only if you ran it now: run `uv run pytest -q` and `uv run ruff check .` and quote
   the result. If there is no Docker setup yet, say the infrastructure document covers a local setup.
6. Draw Mermaid from the actual code. Run `uv run pytest tests/unit/test_phase_doc_checks.py -q`, and say
   the diagrams were checked for structure only. Never say they were rendered or validated.
7. In the Q&A file cover Categories A to M of section 6.2, in the format of section 6.3 and at the four
   difficulty levels of section 6.5. Skip a category that does not apply and say so. In Category M never
   invent a personal experience: leave a placeholder for the owner.
8. Never write a secret. Never edit `CLAUDE.md`, `PLAN.md`, `TASKS.md`, `MEMORY.md` or any test: report
   what should change instead.

Return the completion report of section 7, step 6 (a status for each deliverable, diagrams, links, test
results, known gaps) and the four paths. Say that phase N must be removed from `OWED` in
`tests/unit/test_phase_doc_checks.py`.
