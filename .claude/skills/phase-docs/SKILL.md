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

1. Read `docs/09_PHASE_DOCUMENTATION.md` in full. It is the specification: follow its structure and rules.
2. Find what the phase changed. Take its rows from `TASKS.md`; each names a branch. For each branch find
   its merge commit with `git log --merges --first-parent --grep "<branch>" --format="%h %s"` and read
   what it changed with `git diff <hash>^1 <hash> --stat`. Then read the code. Never credit this phase
   with a later phase's work.
3. Document only what exists. Mark each item implemented, partial, planned, or a future recommendation.
   Cite file paths in backticks: a test fails on any cited path that does not exist. On a line that
   names a planned, removed or historical file, use that word.
4. Write these files, creating the folders if missing. If one exists, update it in place and keep what is
   still true:
   - `internal/explain_codebase/Phase<N>_explained.md`
   - `internal/design_evolution/Phase<N>_Project_System_Design_Evolution.md`
   - `internal/Infra_design_evolution/Phase<N>_Infra_design_evolution.md`
   - `internal/QnA/Phase<N>_Interview_QnA.md`
5. Claim a test passed only if you ran it now: run `uv run pytest -q` and `uv run ruff check .` and quote
   the result. If there is no Docker setup yet, say the infrastructure document covers a local setup.
6. Draw Mermaid from the actual code. Run `uv run pytest tests/unit/test_phase_doc_checks.py -q`, and say
   the diagrams were checked for structure only. Never say they were rendered or validated.
7. Section 6.2 of the spec is incomplete: it stops partway through Category E. Cover Categories A to E,
   and state in the Q&A file that later categories were never specified. Do not invent them.
8. Never write a secret. Never edit `CLAUDE.md`, `PLAN.md`, `TASKS.md`, `MEMORY.md` or any test: report
   what should change instead.

Return the four paths, the check results, and one line each on anything you could not document. Say that
phase N must be removed from `OWED` in `tests/unit/test_phase_doc_checks.py`.
