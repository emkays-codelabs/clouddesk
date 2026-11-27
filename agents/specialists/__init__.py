"""Specialist agents (CLAUDE.md 7.1): one class per role, each a thin wrapper over rules and tools.

Every `run`-style method returns `(result, status, usage, ms, calls)` so a graph node can record
telemetry: `status` is "ok" or "fallback" (the model failed and the rules answered), `usage` is the
`TokenUsage` spent, `ms` the wall time and `calls` the tool calls made. Must NOT: write SQL, call a
model except through `call_structured`, or call a tool except through the `ToolRegistry`.
"""
