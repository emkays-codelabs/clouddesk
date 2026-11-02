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
   single source of truth and splitting it is the owner's call. Measured later (section 7), `CLAUDE.md` is about
   11,000 tokens: roughly $0.04 at a session start and $0.001 a turn, so splitting it is for tidiness, not cost.

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
- **Two-turn test: run 2026-11-02, with a caveat.** Two headless sessions (`claude -p`, Claude Code 2.1.104,
  model `sonnet`) in this repository, five seconds apart:

  | | Cache write | Cache read | Fresh input |
  |---|---|---|---|
  | Call 1 | 45,760 | 0 | 4 |
  | Call 2 | 31,204 | 14,619 | 4 |

  **Caching works:** call 2 read 14,619 tokens from the cache. **But only about a third of the starting
  context was reused between sessions.** Call 2 rewrote 31,204 of roughly 45,800 tokens even though nothing
  changed between the calls. The follow-up below found why.
- **Cost of starting a session:** about 45,800 tokens of context before the first message, which cost $0.29
  on the first call and $0.20 on the second. The follow-up below says what that is made of.
- **TTL observed:** every cache write was a one-hour write (`ephemeral_1h`), and none was five-minute. Per the
  docs that is the default on a Claude subscription within plan usage, so on this login the TTL decision
  above is already answered in practice. It would matter again on an API key, or once usage credits apply.
- **Not covered:** this ran on the terminal CLI, not on the editor session that applied this setup. Run
  `/usage` in that session after its first response to read its `Prompt cache (main)` line.
- **Follow-up: why reuse is partial (2026-11-02, about 40 headless calls, about $3).** The first-pass guesses
  were wrong, so this replaces them.
  - **Inside one conversation caching is complete.** Three turns of one resumed session: turn 1 read 14,619 of
    45,838 tokens ($0.203); turns 2 and 3 read 45,834 and 45,896 of about 45,900 (100%), wrote 62 each, and
    cost $0.023. Only the first request of a new session, or of a new subagent, pays the partial price.
  - **It is not this repository.** In an empty directory with no `CLAUDE.md`, no rules and no git, a new
    session still rewrote 14.2k tokens. The repository's own context adds about 17,000 tokens (45,838 against
    28,777) and is stable.
  - **It is not the per-machine details.** `--exclude-dynamic-system-prompt-sections`, which moves the cwd,
    environment, memory paths and git status out of the system prompt, changed nothing (32% before and after).
  - **It is not MCP size.** `--strict-mcp-config` removed only 124 tokens. Reuse with MCP off was not measured.
  - **It is user-level.** With no user-level settings, the second session reused 100% (20,965 of 20,969 tokens)
    and cost $0.011. Adding settings back one at a time to that clean run, in an empty directory:

    | Added back | Size added | Reuse on the second session |
    |---|---|---|
    | nothing (control) | 0 (20,975 total) | 100% |
    | `effortLevel: medium` | about 0 | 100% |
    | `outputStyle: Explanatory` | 354 | 68% |
    | `superpowers` plugin | 3,073 | 61% |
    | `vercel` plugin | 4,842 | 57% |
    | `slack` and `supabase` plugins | 257 | 69% |
    | all 11 plugins | 7,469 | 51% |

    Any one of the output style or a plugin is enough to cut reuse off at the same point, about 14,600 tokens
    in, even though their text is static. Why was not determined. It looks like Claude Code stops reusing the
    later part of the prefix once the system prompt is customised, but that is a guess. The numbers are worth
    reporting upstream.
  - **Nothing in this repository fixes it.** Restoring full reuse needs the output style and every plugin off,
    which is not a reasonable setup. Options, all yours to choose: accept it (about $0.18 extra per new session
    or subagent start); or disable plugins this project does not need in `.claude/settings.local.json`, which
    is git-ignored, to shrink the start (`vercel` is the largest at 4,842 tokens, `superpowers` next at 3,073).
    That shrinks the cost but does not restore reuse while anything else stays on. `vercel` and `supabase`
    will be useful again around Phases 12 and 13, so it is not obvious they should go.
  - **`CLAUDE.md` is a small lever.** About 11,000 tokens, so roughly $0.04 at a session start and $0.001 a
    turn. Splitting it is worth doing for tidiness, not for cache cost.

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
