# ADR-0012: The harder evaluation bar and a red-team set

## Status

Accepted on 2026-11-27 (owner approval in chat). This is decision D6 in `CLAUDE.md` section 20. The decision is taken; the v1 gate in section 13 stays the only gate that runs until the red-team dataset and the harder metrics exist.

## Context

The upstream product requirements document (PRD) section 8 sets a harder bar for the full product: triage at least 0.90, Recall@10 at least
0.90, faithfulness at least 0.92, tool-call correctness at least 0.95, escalation recall at least 0.98, and
zero successful red-team injections. The v1 gate in `CLAUDE.md` section 13 is lower: classification 0.80,
retrieval hit-rate@3 0.75, escalation correctness 0.90, citation rate 0.90 and grounding rate 0.90.

## Decision

Raise the gate to the upstream PRD bar (triage 0.90, Recall@10 0.90, faithfulness 0.92, tool-call correctness 0.95, escalation recall 0.98) and add a red-team dataset where zero successful injections is required. No threshold is lowered to make a run pass, and the harder bar is measured on a real model as well as the fake one.

## Consequences

If adopted: the Phase 14 gate changes and new datasets are needed. If not adopted: the v1 thresholds stay
the only ones that fail the build, and prompt-injection resistance is checked only by the single `CD-1013`
case. No threshold may be lowered to make a run pass.
