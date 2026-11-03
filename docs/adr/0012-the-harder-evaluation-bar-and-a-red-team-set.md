# ADR-0012: The harder evaluation bar and a red-team set

## Status

Proposed. This is decision D6 in `CLAUDE.md` section 20. It is not taken.

## Context

The upstream PRD section 8 sets a harder bar for the full product: triage at least 0.90, Recall@10 at least
0.90, faithfulness at least 0.92, tool-call correctness at least 0.95, escalation recall at least 0.98, and
zero successful red-team injections. The v1 gate in `CLAUDE.md` section 13 is lower: classification 0.80,
retrieval hit-rate@3 0.75, escalation correctness 0.90, citation rate 0.90 and grounding rate 0.90.

## Decision

Not taken. The question is whether to raise the gate and add a red-team dataset.

## Consequences

If adopted: the Phase 14 gate changes and new datasets are needed. If not adopted: the v1 thresholds stay
the only ones that fail the build, and prompt-injection resistance is checked only by the single `CD-1013`
case. No threshold may be lowered to make a run pass.
