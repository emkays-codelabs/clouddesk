# Claude Code setup: suggestions and open checks

Written 2026-11-02 while applying the cost-governance prompt (local, not committed) to this repository.
This is the only place that proposes changes to a protected file. `CLAUDE.md` was read and not edited.

## 1. Protected files

| File | Where | Lines |
|---|---|---|
| `CLAUDE.md` | repository root | 694 |
| `SKILLS.md` | none exists | not created |

The prompt's verification step expects a protected `CLAUDE.md` of 200 lines or fewer. This one is 694.
That is reported, not changed.

## 2. Suggested changes to `CLAUDE.md`

Apply these between sessions: `CLAUDE.md` is read once at session start, so an edit applies after
`/clear`, `/compact` or a restart.

1. **Point to the setup.** Add to section 4.3 (folder layout) and section 14 (commands):

   ```text
   .claude/       settings.json · agents/ · skills/ · rules/ · hooks/pre-commit.sh
   /plan  /implement  /test  /review  /consult-opus  /cost-report  /pr-review
   ```

2. **Add a short Cost and delegation paragraph** (ready to paste, under section 18):

   > Work runs on Sonnet by default. Opus runs only in the `planner` and `opus-consultant` agents; Haiku
   > runs `Explore` and `log-triage`. Finish one task before starting another, keep one session per topic,
   > and do not switch models mid-task. The full rules are in `.claude/rules/cost-and-delegation.md`.

3. **Add a chunking row to the section 1.1 comparison table.** The upstream LLD sizes chunks at 600 tokens
   with an 80-token overlap and keeps tables whole; CloudDesk uses 900 characters with 150 overlap
   (section 8). It is a deliberate v1 choice that the table does not yet list.

4. **Move path-specific detail out.** At 694 lines the file loads in full every session. Sections 8 (RAG),
   9 (guardrails) and 11 (frontend) apply only when working in `rag/`, `agents/` or `frontend/`, so they
   would fit as `paths:` rules and load on demand. This is a suggestion, not a request: `CLAUDE.md` is the
   single source of truth and splitting it is the owner's call.

5. **No conflict with the cost plan.** `CLAUDE.md` does not ask for an auto-commit after every change. Its
   rule that no one pushes without the owner saying so is repeated in the agents and the cost rule.

## 3. `SKILLS.md`

None exists. Claude Code loads `.claude/skills/<name>/SKILL.md`. The existing `clouddesk-support` skill is
kept unchanged; the seven new skills sit beside it.

## 4. Per-run budgets (guidelines, not limits)

Exceeding one is a signal to split the task. Scale up for a larger repository.

| Agent | Max tool calls per run | `maxTurns` set |
|---|---|---|
| `Explore` | 10 | 30 |
| `log-triage` | 10 | 15 |
| `opus-consultant` | 10 | 10 |
| `code-reviewer` | 30 | 60 |
| `planner` | 40 | 40 |
| `test-engineer` | 80 | 120 |
| `implementer` | 120 | 120 |

## 5. Skipped agents and skills

| Skipped | Why | Add it when |
|---|---|---|
| `architect` agent | One module today (`backend/app/`) and no ADR folder | `rag/`, `agents/` and `frontend/` exist, or an ADR folder appears |
| `wait` skill | No job runs for more than a few minutes (the suite takes about 3 seconds) | Phase 14 adds Terraform and image builds |
| `fix-issue` skill | No issue tracker is referenced: `TASKS.md` is the tracker | GitHub Issues is adopted |

## 6. Where the prompt and the official docs disagree

The docs won in each case. Source: `code.claude.com/docs`, read 2026-11-02.

| The prompt says | The docs say | What was done |
|---|---|---|
| Editing CLAUDE.md, rules, agents or settings mid-session invalidates the cache | CLAUDE.md is read once at start, so an edit neither breaks the cache nor applies. Skills, agents and hooks append and never invalidate. Settings hot-reload. Model switches, MCP changes and denying a whole tool do invalidate. | The cost rule states the real triggers |
| `Agent(opus-consultant)` restricts what a subagent may spawn | The type list is ignored inside a subagent definition | Agents list plain `Agent`; the restriction is written in their instructions |
| A forked skill returns its result | Forked skills run in the background by default | Every forked skill sets `background: false` |
| Subagents share the TTL decision | Subagents get five minutes unless `subagentPromptCacheTtl` is set (v2.1.242 or later) | Left unset; see section 7 |
| `omitClaudeMd` is usable | Documented, but needs v2.1.271 or later | Set on `log-triage` and marked unverified |

## 7. Caching

- **Platform:** first-party API (no Vertex, Bedrock or Foundry variable set).
- **Claude Code version:** the CLI on this PATH reports 2.1.104. The session that applied this setup is a
  different build and its version could not be read from here. Run `claude --version` or `/status` where
  you launch it. Several keys below are version-gated.
- **Model ids pinned:** `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`.
- **TTL: `<DECIDE: probe result>`.** Not set. Prices from the official pricing page, 2026-11-02, per million
  tokens:

  | Model | Base input | 5m write | 1h write | Cache read | Output |
  |---|---|---|---|---|---|
  | Opus 5.5 | $4 | $5 | $8 | $0.20 | $20 |
  | Sonnet 5.5 | $2 | $2.50 | $4 | $0.10 | $10 |
  | Haiku 5.5 (up to 100k tokens) | $0.10 | $0.125 | $0.20 | $0.01 | $0.50 |

  For Sonnet, a one-hour write costs $1.50 more per million tokens than a five-minute write. Each idle gap
  of 5 to 60 minutes forces the five-minute cache to be rewritten at $2.50 instead of read at $0.10, which
  is $2.40 saved. So the longer TTL pays back once the prefix would otherwise expire about once per write,
  and loses if you never pause longer than five minutes. On a Claude subscription the main conversation
  already gets one hour within plan usage; on an API key it gets five minutes. Keys, if you choose it:
  `promptCacheTtl` or `CLAUDE_CODE_PROMPT_CACHE_TTL` for the main conversation, and `subagentPromptCacheTtl`
  or `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` for subagents, all v2.1.242 or later.
- **Two-turn test: pending.** In a fresh session: send one short message and note the cache-write tokens in
  `/usage`; send a second within a minute. The second must show cache-read tokens. If it shows none, caching
  is not working: stop and record the Claude Code version and platform here.

## 8. Items to verify on the pinned version

| Item | Status |
|---|---|
| `env` keys: the three model pins, `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (v2.1.217 or later) | documented, untested here |
| `effort` agent field | documented, untested |
| Hook JSON format and exit code 2 | documented; the script's logic was run by hand, a live session was not |
| `omitClaudeMd` | needs v2.1.271 or later; unverified |
| `Agent` tool in a subagent's `tools` | documented; unverified that `implementer` can spawn `opus-consultant` |
| Unscoped rule `cost-and-delegation.md` loads every session | unverified |
| Skill names `plan`, `review`, `test` do not collide with built-in commands | unverified |
| Agent identity appears in usage data (per-agent cost) | unknown; `cost-report` says so when absent |

## 9. Parallel work

At most 3 agents, one git worktree each (`isolation: worktree`), each given an explicit file scope. Tasks
that touch the same file, migration, lock file or schema run in sequence. In this repository that includes
`TASKS.md`, `PLAN.md` and `MEMORY.md`, which every task edits.

## 10. Remaining placeholders

- `<DECIDE: probe result>`: the cache TTL (section 7).

There are no `<PIN: ...>` or `<TODO: ...>` placeholders: the three model ids were stated in the model list
for the first-party API, and the commands came from `pyproject.toml` and the `Makefile`.
