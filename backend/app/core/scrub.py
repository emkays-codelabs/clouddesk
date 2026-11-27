"""Secret scrub (N7, CLAUDE.md 7.5): remove card numbers, keys, tokens and passwords from text.

Does: `SECRET_PATTERNS` names each secret shape; `scrub(text)` replaces every match with
`[REDACTED:<kind>]` (card-like digit runs only when they pass the Luhn check, so order numbers
and phone numbers survive); `find_secrets(text)` lists the kinds present. Scrubbing is idempotent
and leaves clean text byte-for-byte unchanged. Used by memory notes (Phase 8) and by output
validation (P7-3). Must NOT: import `agents/`, call a model, log the matched value.
"""

import re

# Order matters: a JWT or bearer token is consumed before the looser patterns see it.
SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "api_key": re.compile(r"\bsk-(?:[A-Za-z]+-)*[A-Za-z0-9_-]{16,}"),
    "password": re.compile(r"\b(?:password|passwd|pwd)\b\s*[:=]\s*\S{6,}", re.IGNORECASE),
    # Candidate digit runs; a run is a card only if it also passes the Luhn check.
    "card_number": re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])"),
}


def luhn_valid(digits: str) -> bool:
    total, flip = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if flip:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
        flip = not flip
    return total % 10 == 0


def _is_card(match: re.Match[str]) -> bool:
    digits = re.sub(r"\D", "", match.group(0))
    return 13 <= len(digits) <= 19 and luhn_valid(digits)


def scrub(text: str | None) -> str:
    """`text` with every secret replaced by `[REDACTED:<kind>]`; clean text is unchanged."""
    out = text or ""
    for kind, pattern in SECRET_PATTERNS.items():
        marker = f"[REDACTED:{kind}]"
        if kind == "card_number":
            out = pattern.sub(lambda m, k=marker: k if _is_card(m) else m.group(0), out)
        else:
            out = pattern.sub(marker, out)
    return out


def find_secrets(text: str | None) -> list[str]:
    """The kinds of secret present in `text`, in table order."""
    body = text or ""
    found = []
    for kind, pattern in SECRET_PATTERNS.items():
        if any(kind != "card_number" or _is_card(m) for m in pattern.finditer(body)):
            found.append(kind)
    return found
