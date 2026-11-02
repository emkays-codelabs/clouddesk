---
name: pr-review
description: Review a GitHub pull request by number for correctness and breaches of the CloudDesk rules. Read-only; never posts a comment.
context: fork
agent: code-reviewer
background: false
disable-model-invocation: true
argument-hint: "[pull request number]"
---

Review pull request $ARGUMENTS in `emkays-codelabs/clouddesk`.

Read it with `gh pr view $ARGUMENTS` and `gh pr diff $ARGUMENTS`. Do not post a comment, approve, or merge:
that is the owner's decision. Return the ranked findings list only.
