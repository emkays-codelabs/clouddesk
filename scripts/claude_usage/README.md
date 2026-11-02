# Claude Code usage report

Placeholder. No script exists yet, and the `cost-report` skill says so when it finds none.

A report here should be standard-library only and print, for the last N days:

- cost per day
- cache-read share of input tokens: `cache_read / (cache_read + cache_creation + uncached input)`
- cost per agent type, only if the usage data names the agent (unverified on this version)

Where the numbers come from, in order of effort:

1. `/usage` inside a session. After the first response it shows a `Prompt cache (main)` line with the hit
   ratio, miss count and likely cause of the last miss (needs Claude Code v2.1.251 or later).
2. `claude -p "hello" --output-format json`, then `usage.cache_creation`: one-hour writes appear under
   `ephemeral_1h_input_tokens` and five-minute writes under `ephemeral_5m_input_tokens`.
3. The session transcripts under `~/.claude/projects/`, if their fields turn out to carry token counts.

Do not write prices into the script. Read them from the official pricing page each time they are needed.
