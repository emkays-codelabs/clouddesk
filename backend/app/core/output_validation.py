"""Customer output validation (N5, CLAUDE.md 9): nothing unsafe or unsupported reaches a customer.

Does: `validate_customer_output(text, cited_chunks, customer_context)` blocks internal URLs
(localhost, loopback, `*.internal`, `*.local`, private ranges, `kb://` paths), secrets
(`SECRET_PATTERNS`) and another customer name or email (from `customer_context["other_customers"]`),
and scores groundedness: each claim sentence is checked by token overlap against the cited chunks,
and the score is the share of supported claims. Any failure gives risk `high`. `next_step` is the
revise-once policy: a groundedness miss earns one revise then escalates; a leak escalates at once.
Must NOT: import `agents/`, call a model, or revise the text itself.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.scrub import find_secrets

GROUNDEDNESS_THRESHOLD = 0.8
MAX_REVISIONS = 1
CLAIM_SUPPORT = 0.6  # share of a claim content words that a cited chunk must contain
MIN_CLAIM_WORDS = 4  # shorter sentences are pleasantries, not claims

INTERNAL_URL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\blocalhost\b",
        r"\b127\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        r"\b0\.0\.0\.0\b",
        r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        r"\b192\.168\.\d{1,3}\.\d{1,3}\b",
        r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b",
        r"\b[\w-]+(?:\.[\w-]+)*\.(?:internal|local|corp|intranet)\b",
        r"\bkb://",
    )
)

_STOP = frozenset(
    "a an the and or but of to in on at by for from with is are was were be been we you your our "
    "it this that these those will can could would should may have has had not no do does did as "
    "if so then than into out up about hi hello thanks thank please".split()
)
_WORD = re.compile(r"[a-z0-9]+")
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_HARD = {"internal_url", "secret", "other_customer_data"}


@dataclass
class OutputValidation:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    groundedness: float = 1.0
    risk: Literal["low", "high"] = "low"


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 1}


def _chunk_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    if isinstance(chunk, Mapping):
        return " ".join(str(chunk.get(k, "")) for k in ("title", "snippet", "text"))
    return " ".join(str(getattr(chunk, k, "")) for k in ("title", "snippet", "text"))


def groundedness(text: str, cited_chunks: Iterable[Any]) -> float:
    """Share of claim sentences whose content words are mostly present in one cited chunk."""
    chunk_words = [_words(_chunk_text(c)) for c in cited_chunks]
    claims = []
    for sentence in _SENTENCE.split(text):
        if not sentence.strip() or sentence.strip().endswith("?"):
            continue
        words = _words(sentence)
        if len(words) >= MIN_CLAIM_WORDS:
            claims.append(words)
    if not claims:
        return 1.0
    supported = sum(
        any(len(c & cw) / len(c) >= CLAIM_SUPPORT for cw in chunk_words) for c in claims
    )
    return supported / len(claims)


def _other_customer_terms(context: Mapping[str, Any] | None) -> list[str]:
    others = (context or {}).get("other_customers") or []
    return [str(o).strip().lower() for o in others if str(o).strip()]


def validate_customer_output(
    text: str,
    cited_chunks: Sequence[Any],
    customer_context: Mapping[str, Any] | None = None,
) -> OutputValidation:
    body = text or ""
    reasons: list[str] = []
    if any(p.search(body) for p in INTERNAL_URL_PATTERNS):
        reasons.append("internal_url")
    if find_secrets(body):
        reasons.append("secret")
    lowered = body.lower()
    if any(term in lowered for term in _other_customer_terms(customer_context)):
        reasons.append("other_customer_data")
    score = groundedness(body, cited_chunks)
    if score < GROUNDEDNESS_THRESHOLD:
        reasons.append("ungrounded")
    ok = not reasons
    return OutputValidation(ok, reasons, round(score, 3), "low" if ok else "high")


def _hard_failure(result: OutputValidation) -> bool:
    return bool(_HARD & set(result.reasons))


def should_revise(result: OutputValidation, revisions_done: int) -> bool:
    """One revise for a groundedness miss; leaks are never retried."""
    return not result.ok and not _hard_failure(result) and revisions_done < MAX_REVISIONS


def should_escalate(result: OutputValidation, revisions_done: int) -> bool:
    return not result.ok and not should_revise(result, revisions_done)


def next_step(
    result: OutputValidation, revisions_done: int
) -> Literal["send", "revise", "escalate"]:
    if result.ok:
        return "send"
    return "revise" if should_revise(result, revisions_done) else "escalate"
