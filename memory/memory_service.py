"""Memory service (CLAUDE.md 7.5, F4, F11, N7): recall prior notes, record a finished resolution.

Does: `MemoryService(long_term, scrub)` offers `recall_customer(customer_id)` (up to 10 notes) and
`record_resolution(...)`, which writes a past issue, the first three troubleshooting steps and a
resolution note for that one customer. Every note passes the injected `scrub` first (the backend
passes `app.core.scrub.scrub`), so cards, keys and passwords never reach `customer_memory`. A note
that contains the raw ticket body is dropped. Note text is deterministic, so recording the same
resolution twice leaves one of each (exact duplicates are skipped by `LongTermMemory`).
Must NOT: import `backend/app`, take another customer's id, or store a ticket body.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from memory.long_term import LongTermMemory, Note

MAX_STEPS = 3
MIN_BODY_CHARS = 20
DEFAULT_CONFIDENCE = 0.9


@dataclass
class RecordReport:
    written: list[Note] = field(default_factory=list)
    skipped: int = 0


class MemoryService:
    def __init__(self, long_term: LongTermMemory, scrub: Callable[[str], str]) -> None:
        self._long_term = long_term
        self._scrub = scrub

    async def recall_customer(self, customer_id: str) -> list[Note]:
        return await self._long_term.recall(customer_id)

    async def record_resolution(
        self,
        customer_id: str,
        ticket_id: str,
        category: str,
        summary: str,
        steps: Sequence[str],
        resolution: str,
        ticket_body: str | None = None,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> RecordReport:
        """Write the past issue, the first three steps and the resolution note; skip repeats."""
        candidates = [("past_issue", f"{category}: {summary}")]
        candidates += [
            ("troubleshooting", f"Step {n}: {step}") for n, step in enumerate(steps[:MAX_STEPS], 1)
        ]
        candidates.append(("note", f"Resolution: {resolution}"))

        body = (ticket_body or "").strip()
        report = RecordReport()
        for memory_type, text in candidates:
            clean = self._scrub(text)
            if len(body) >= MIN_BODY_CHARS and body in clean:
                report.skipped += 1
                continue
            note = await self._long_term.remember(
                customer_id, memory_type, clean, confidence, source_ticket_id=ticket_id
            )
            if note is None:
                report.skipped += 1
            else:
                report.written.append(note)
        return report
