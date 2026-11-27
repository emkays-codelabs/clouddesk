"""Prompt-injection scan (N4, CLAUDE.md 9): flag text that tries to instruct the model.

Does: `scan_for_injection(text)` returns the named attack families found (ignore-instructions,
export-all-records, reveal-system-prompt, role-override, tool-call smuggling, delimiter escape).
`drop_injected_chunks(doc)` is the retriever's `chunk_filter` hook: it returns False for a
retrieved chunk that carries an instruction, so a poisoned knowledge article never reaches a prompt.
Flagging is deterministic and never blocks the ticket: a flagged ticket is still handled, as data,
and raises risk to high in the graph (Phase 10).
Must NOT: import `agents/` or `rag/` (a chunk is any object with a `.text`), call a model.
"""

import re
from dataclasses import dataclass
from typing import Protocol


def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


_NOUNS = r"(instructions?|rules?|prompts?|guidelines?|directions?|messages?)"

INJECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "ignore_instructions": _re(
        r"\b(ignore|disregard|forget|override|bypass)\b\s+(all\s+|any\s+|the\s+|your\s+)*"
        rf"(previous|prior|above|earlier|preceding|safety)?\s*{_NOUNS}"
    ),
    "export_all_records": _re(
        r"\b(export|dump|list|send|email|leak|exfiltrate)\b[^.\n]{0,40}\b(all|every|entire|whole)\b"
        r"[^.\n]{0,30}\b(customers?|users?|records?|accounts?|emails?|tickets?|data)\b"
    ),
    "reveal_system_prompt": _re(
        r"\b(reveal|show|print|repeat|output|display|leak)\b[^.\n]{0,40}"
        r"\b(system\s+prompt|hidden\s+(instructions?|prompt)|initial\s+instructions?|"
        r"instructions?\s+you\s+were\s+given)"
    ),
    "role_override": _re(
        r"\byou\s+are\s+now\b|\bfrom\s+now\s+on\b[^.\n]{0,30}\b(act|behave|you)\b|"
        r"\b(admin|developer|root|god|debug)\s+mode\b|\bact\s+as\s+(dan|an?\s+unrestricted)|"
        r"\bjailbreak"
    ),
    "tool_call_smuggling": _re(
        r"\b(call|invoke|run|execute|use)\s+(the\s+)?(tool\s+)?"
        r"(create_refund_request|reset_demo_setting|create_escalation|update_ticket)\b|"
        r"[\"']tool[\"']\s*:|\"function_call\"|<tool_call>"
    ),
    "delimiter_escape": _re(
        r"</?\s*untrusted_content|<\|im_(start|end)\|>|<\|system\|>|\[/?INST\]|"
        r"^\s*(system|assistant)\s*:",
    ),
}


@dataclass(frozen=True)
class InjectionScan:
    flagged: bool
    flags: tuple[str, ...]


def scan_for_injection(text: str) -> InjectionScan:
    """Named injection families found in `text`; empty text is clean."""
    flags = tuple(name for name, p in INJECTION_PATTERNS.items() if p.search(text or ""))
    return InjectionScan(bool(flags), flags)


class _HasText(Protocol):
    text: str


def drop_injected_chunks(chunk: _HasText) -> bool:
    """`chunk_filter` hook for the retriever: True keeps the chunk, False drops it."""
    return not scan_for_injection(chunk.text).flagged
