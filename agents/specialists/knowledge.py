"""Knowledge Agent (F5, F6): cited evidence and similar resolved cases. No model call.

Does: `run` searches the knowledge base through the `search_docs` tool and returns `Evidence`
(id, title, `kb://` source, snippet, score), dropping any chunk that carries an instruction (a
poisoned article is the same attack as a poisoned ticket, CLAUDE.md 9). `similar_cases` ranks the
previously resolved cases in `sample_data/previous_resolutions.json` by Jaccard overlap of word sets
and returns the best few as `PreviousCase`.
Must NOT: call a model, or let retrieved text act as an instruction.
"""

import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from agents.specialists.common import ToolCallRecord, call_tool, elapsed_ms
from app.core.injection_guard import scan_for_injection
from app.schemas.workflow import Evidence, PreviousCase, TokenUsage
from app.tools.registry import ToolRegistry

TOP_K = 5
MAX_CASES = 3
MIN_SIMILARITY = 0.05
_WORD = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset(
    "the and for with that this from have has had not are was were but you your our can will "
    "all any out about they them then than into its been when what which would could should".split()
)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORD.findall(text.lower()) if w not in _STOP)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


@lru_cache(maxsize=4)
def _load_resolutions(sample_dir: str) -> tuple[dict[str, Any], ...]:
    path = Path(sample_dir) / "previous_resolutions.json"
    return tuple(json.loads(path.read_text("utf-8")))


class KnowledgeAgent:
    def __init__(self, registry: ToolRegistry, sample_data_dir: str = "./sample_data") -> None:
        self._registry = registry
        self._sample_dir = sample_data_dir

    async def run(
        self, query: str, top_k: int = TOP_K
    ) -> tuple[list[Evidence], str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        calls: list[ToolCallRecord] = []
        record = await call_tool(
            self._registry, calls, "search_docs", {"query": query[:1000], "top_k": top_k}
        )
        evidence: list[Evidence] = []
        if record.ok:
            for item in record.data:
                text = f"{item.get('title', '')}\n{item.get('snippet', '')}"
                if scan_for_injection(text).flagged:
                    continue
                evidence.append(Evidence.model_validate(item))
        status = "ok" if record.ok else "fallback"
        return evidence, status, TokenUsage(), elapsed_ms(started), calls

    async def similar_cases(
        self, text: str, limit: int = MAX_CASES
    ) -> tuple[list[PreviousCase], str, TokenUsage, int, list[ToolCallRecord]]:
        started = time.perf_counter()
        query = _tokens(text)
        scored = []
        for case in _load_resolutions(self._sample_dir):
            doc = _tokens(f"{case['subject']} {case['summary']} {' '.join(case['steps'])}")
            scored.append((jaccard(query, doc), case))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        cases = [
            PreviousCase(
                ticket_number=case["key"],
                subject=case["subject"],
                resolution_summary=case["resolution"],
                similarity=round(min(score, 1.0), 4),
            )
            for score, case in scored[:limit]
            if score >= MIN_SIMILARITY
        ]
        return cases, "ok", TokenUsage(), elapsed_ms(started), []
