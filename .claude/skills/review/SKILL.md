---
name: review
description: Review the current working diff, a branch or a path for correctness and breaches of the CloudDesk rules. Read-only; returns a ranked findings list.
context: fork
agent: code-reviewer
background: false
argument-hint: "[branch or path, or leave blank for the working diff]"
---

Review this: $ARGUMENTS

If no argument was given, review `git diff` and `git diff --cached`. Return the ranked findings list only.
