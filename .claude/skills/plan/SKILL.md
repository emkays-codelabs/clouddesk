---
name: plan
description: Write an implementation plan for a TASKS.md task or a feature request. Use before changing code that touches more than one file or layer.
context: fork
agent: planner
background: false
argument-hint: "[task id or topic, e.g. P2-1]"
---

Plan this: $ARGUMENTS

Write the plan to `docs/plans/<topic>.md` and return only the file path.
