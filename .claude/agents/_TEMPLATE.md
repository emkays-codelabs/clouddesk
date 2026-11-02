# Agent template

This file is documentation, not an agent. Its frontmatter is shown inside a code block on purpose:
Claude Code loads every `.md` file in this folder whose frontmatter starts on line 1, so a real
frontmatter block here would register a phantom agent.

Copy the block below into a new `<name>.md`, fill it in, and keep the last line.

```markdown
---
name: <unique-name, no colon, 256 characters or fewer>
description: Delegate here to <what it does>. Use when <the trigger>.
model: <haiku | sonnet | opus>
effort: <low | medium | high>
tools: <comma-separated; list Agent only if it may spawn subagents>
maxTurns: <number>
---

<Numbered instructions. Say what it must never do.>

Return limit: <words or lines, and what the answer contains>.
```

Rules for this repository:
- `opus` appears only on `planner`, `opus-consultant`, and `architect` if it is ever created.
- `Agent(name)` in a subagent's `tools` does not restrict which agents it can spawn: the docs say the
  type list is ignored there. State the restriction in the instructions instead.
- A search agent replaces the built-in only if its file and its `name` are both exactly `Explore`.
- Every instruction set ends with a return limit.
