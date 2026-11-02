---
name: cost-report
description: Show Claude Code cost and prompt-cache health for the last 7 days. Use when usage looks high or after changing the .claude setup.
model: haiku
argument-hint: "[days, default 7]"
---

Report cost and cache health for the last $ARGUMENTS days (7 if none given).

1. If `scripts/claude_usage/report.py` exists, run `uv run python scripts/claude_usage/report.py --days 7`
   and show its table. If it does not exist, say so: only a README is there until someone writes it.
2. Tell the user to run `/usage`. After the first response its `Prompt cache (main)` line gives the
   session's hit ratio, miss count and likely cause of the last miss.
3. Show the cache-read share of input tokens: `cache_read / (cache_read + cache_creation + uncached input)`.
   A drop after a rollout means something is breaking the cache.
4. Show cost per agent type only if the usage data names the agent. Otherwise print
   "per-agent breakdown unavailable on this version".

Do not estimate a cost from memory. Prices come from the official pricing page.
