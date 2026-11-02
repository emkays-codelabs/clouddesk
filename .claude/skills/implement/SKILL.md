---
name: implement
description: Execute an approved plan from docs/plans/. Writes the failing test, makes it pass, runs lint, and updates TASKS.md and MEMORY.md.
context: fork
agent: implementer
background: false
disable-model-invocation: true
argument-hint: "[plan path, e.g. docs/plans/p2-1.md]"
---

Execute this approved plan: $ARGUMENTS

Stay inside the files the plan lists. Report only the changed files and any open issues.
