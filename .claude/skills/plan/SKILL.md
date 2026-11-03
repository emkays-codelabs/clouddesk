---
name: plan
description: Write an implementation plan for a TASKS.md task or a feature request. Use before changing code that touches more than one file or layer.
context: fork
agent: planner
background: false
argument-hint: "[task id or topic, e.g. P2-1]"
---

Plan this: $ARGUMENTS

Write the plan to `docs/plans/<task-id>.md` with the id in lower case (`p2-1.md`), or a short slug when the
request has no task. Plans are working files: they are not committed (the folder is git-ignored apart from
`.gitkeep`) and are deleted once the task merges. Return only the file path.
