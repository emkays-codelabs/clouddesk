"""Find the knowledge articles that answer a query: hybrid search, fusion, rerank, sufficiency.

Does: rewrite a query into 1-3 sub-queries (deterministic, optional injected `rewriter`), run
semantic search (vector store) and BM25 keyword search (`rank_bm25`) per sub-query, fuse the
rankings with reciprocal rank fusion (k=60), rerank heuristically (category match + title
overlap), optionally rerank through an injected `llm_rerank` hook, keep one hit per article, and
run a deterministic sufficiency check that may retrieve ONE more time against the terms it found
missing, then stops. Modes `hybrid` (default), `semantic`, `keyword`; a category filter; `top_k`.
Results are cached for 300 s through an injected cache object (`get(key)`, `set(key, value, ttl)`)
under `rag:{mode}:{category}:{top_k}:{query}`. `chunk_filter` is the hook point where retrieved
chunks are screened before they are ranked (P7-2). Must NOT: know about tickets, customers or
workflows, import `app.*` or `agents/` (the Redis cache is passed in), call an LLM itself (hooks
are injected), or know which vector store is live.
"""

import inspect
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from rank_bm25 import BM25Okapi

from rag.chunking import Chunk
from rag.embeddings import Embeddings
from rag.vector_store import Document, VectorStoreService

Mode = Literal["hybrid", "semantic", "keyword"]

RRF_K = 60
CACHE_TTL_SECONDS = 300
POOL = 20  # candidates taken from each ranking before fusion
CATEGORY_BONUS = 0.15
TITLE_WEIGHT = 0.5
MIN_TOP_SCORE = 0.3  # below this the best hit is not good enough
MIN_COVERAGE = 0.5  # share of query terms that must appear in the top hits
SNIPPET_CHARS = 240
# Relevance cut-off. The ranking `score` is rank-based, so an unanswerable question still scores
# 0.93-0.96 and cannot be thresholded. What separates answers from padding is how many of the
# query's content words the ARTICLE contains (all its chunks, so the answer does not depend on
# which chunk happened to rank first). Measured over the 16 evaluation cases the expected article
# covers 0.36-0.83 of them (5 or more words in 15 cases); the padding next to it mostly covers
# 0.05-0.3. On four unanswerable questions no article covers more than 0.5 or more than 2 words,
# and three of the four stay at 0.25 or below.
MIN_TERM_COVERAGE = 0.3  # an article below this is not about the query
MIN_MATCHED_TERMS = 2  # one shared word is a coincidence (capped at the number of query words)
RELATIVE_COVERAGE = 0.5  # drop neighbours covering under half of what the best hit covers
STRONG_COVERAGE = 0.4  # "strong" needs this share of the query's words ...
STRONG_MATCHED_TERMS = 3  # ... at least this many words ...
STRONG_RELATIVE = 0.75  # ... and to be close to the best hit, so a neighbour never looks as good

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "a an the and or but of to in on at by for from with without is are was were be been am i "
    "we "
    "you he she it they our your their my me us this that these those there here not no do "
    "does did "
    "can could will would should may might have has had please cant how what why when where "
    "which who whom now still after before since again all any some every each just also very so "
    "as if then than too into out up down over under about get got".split()
)

ChunkFilter = Callable[[Document], bool]
Rewriter = Callable[[str], list[str] | Awaitable[list[str]]]
LlmReranker = Callable[
    [str, list[dict[str, Any]]], list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]
]


class RetrievalCache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int) -> None: ...


@dataclass
class RetrievalResult:
    evidence: list[dict[str, Any]]
    sufficient: bool
    gaps: list[str] = field(default_factory=list)
    passes: int = 1
    cached: bool = False


def _stem(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    """Lower-cased, stop-word-free, lightly stemmed tokens."""
    return [_stem(t) for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


def rewrite_query(query: str) -> list[str]:
    """Up to three sub-queries: the original, a keyword-stripped one and a key-noun variant."""
    original = " ".join(query.split())
    words = [w for w in _TOKEN.findall(original.lower()) if w not in _STOPWORDS and len(w) > 1]
    keywords = " ".join(words)
    # The longest words carry the topic ("quota", "recovery"); short ones are mostly glue.
    key_nouns = " ".join(sorted(dict.fromkeys(words), key=lambda w: (-len(w), w))[:3])
    out: list[str] = []
    for q in (original, keywords, key_nouns):
        if q and q not in out:
            out.append(q)
    return out[:3]


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Sum 1 / (k + rank) over every ranking a document appears in (rank starts at 1)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _slug(heading: str) -> str:
    return "-".join(_TOKEN.findall(heading.lower())) or "overview"


def documents_from_chunks(chunks: list[Chunk], embeddings: Embeddings) -> list[Document]:
    """Turn chunks into vector-store documents carrying the metadata the retriever reads."""
    vectors = embeddings.embed_documents([c.text for c in chunks])
    return [
        Document(
            id=c.id,
            text=c.text,
            vector=v,
            metadata={
                "article_id": c.article_slug,
                "title": c.title,
                "category": c.category,
                "heading": c.heading,
                "source": f"kb://{c.article_slug}#{_slug(c.heading)}",
                "tags": list(c.tags),
            },
        )
        for c, v in zip(chunks, vectors, strict=True)
    ]


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def cache_key(mode: str, category: str | None, top_k: int, query: str) -> str:
    return f"rag:{mode}:{category or ''}:{top_k}:{query}"


_SENTENCE_END = re.compile(r"""[.!?]["')\]]?(?=\s|$)""")


def snippet_of(text: str, limit: int = SNIPPET_CHARS) -> str:
    """A readable excerpt of at most `limit` characters plus an ellipsis, never cut inside a word.

    Prefers the last sentence end past the halfway point, then the last word break; a single
    unbroken run longer than `limit` is hard-cut. The ellipsis marks that more text exists.
    """
    text = text.strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    ends = [m.end() for m in _SENTENCE_END.finditer(window)]
    if ends and ends[-1] >= limit // 2:
        return window[: ends[-1]].rstrip() + "…"
    # Cut at a word break unless the window already ends exactly at one.
    if not text[limit].isspace():
        space = window.rfind(" ")
        if space > 0:
            window = window[:space]
    return window.rstrip().rstrip(",;:-–—(") + "…"


def _evidence(doc: Document, score: float) -> dict[str, Any]:
    body = doc.text.split("\n", 1)[-1].strip()
    article = doc.metadata["article_id"]
    return {
        "id": doc.id,
        "title": doc.metadata["title"],
        "source": doc.metadata["source"],
        "snippet": snippet_of(body),
        "passage": body,
        "score": round(score, 4),
        "url": f"/knowledge/{article}",
        "article_id": article,
    }


class HybridRetriever:
    def __init__(
        self,
        store: VectorStoreService,
        embeddings: Embeddings,
        documents: list[Document],
        *,
        cache: RetrievalCache | None = None,
        chunk_filter: ChunkFilter | None = None,
        rewriter: Rewriter | None = None,
        llm_rerank: LlmReranker | None = None,
    ) -> None:
        self._store = store
        self._embeddings = embeddings
        self._docs = {d.id: d for d in documents}
        self._order = [d.id for d in documents]
        # Every word of every chunk of an article, for the relevance cut-off.
        self._article_words: dict[str, set[str]] = {}
        for d in documents:
            words = self._article_words.setdefault(d.metadata["article_id"], set())
            words.update(tokenize(f"{d.text} {d.metadata.get('title', '')}"))
        corpus = [
            tokenize(f"{d.text} {' '.join(d.metadata.get('tags', []))}") or ["_"] for d in documents
        ]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        self._cache = cache
        self._chunk_filter = chunk_filter
        self._rewriter = rewriter
        self._llm_rerank = llm_rerank
        self.search_calls = 0  # full ranking passes run, for tests and cost tracking

    async def retrieve(
        self,
        query: str,
        *,
        mode: Mode = "hybrid",
        category: str | None = None,
        top_k: int = 5,
        strict_category: bool = True,
    ) -> RetrievalResult:
        """Evidence for `query`. `strict_category=False` makes the category a ranking hint only."""
        key = cache_key(mode, category, top_k, query)
        if self._cache is not None:
            raw = await self._cache.get(key)
            if raw:
                data = json.loads(raw)
                return RetrievalResult(
                    evidence=data["evidence"],
                    sufficient=data["sufficient"],
                    gaps=data["gaps"],
                    passes=data["passes"],
                    cached=True,
                )

        subqueries = await self._subqueries(query)
        flt = {"category": category} if category and strict_category else None
        rankings = await self._rank(subqueries, mode, flt)
        hits = await self._finish(query, rankings, category, top_k)
        sufficient, gaps = self._check(query, hits)
        passes = 1
        if not sufficient and gaps:
            # One more look, aimed at the terms nothing covered; whatever it finds, we stop here.
            passes = 2
            rankings += await self._rank([" ".join(gaps)], mode, flt)
            hits = await self._finish(query, rankings, category, top_k)
            sufficient, gaps = self._check(query, hits)

        # The cut-off runs last, so the sufficiency passes above see the same ranking as before.
        hits = self._relevant(query, hits)
        if not any(h["strength"] == "strong" for h in hits):
            sufficient = False

        if self._cache is not None:
            payload = {"evidence": hits, "sufficient": sufficient, "gaps": gaps, "passes": passes}
            await self._cache.set(key, json.dumps(payload), CACHE_TTL_SECONDS)
        return RetrievalResult(hits, sufficient, gaps, passes)

    async def _subqueries(self, query: str) -> list[str]:
        subs = rewrite_query(query)
        if self._rewriter is not None:
            extra = await _maybe_await(self._rewriter(query))
            subs = list(dict.fromkeys([*subs, *extra]))[:3]
        return subs or [query]

    def _keep(self, doc: Document) -> bool:
        return self._chunk_filter is None or self._chunk_filter(doc)

    async def _rank(
        self, subqueries: list[str], mode: Mode, flt: dict[str, Any] | None
    ) -> list[list[str]]:
        self.search_calls += 1
        rankings: list[list[str]] = []
        for sub in subqueries:
            if mode in ("hybrid", "semantic"):
                hits = await self._store.search(self._embeddings.embed_query(sub), POOL, flt)
                ids = [h.document.id for h in hits if h.score > 0 and self._keep(h.document)]
                if ids:
                    rankings.append(ids)
            if mode in ("hybrid", "keyword"):
                ids = self._keyword(sub, flt)
                if ids:
                    rankings.append(ids)
        return rankings

    def _keyword(self, query: str, flt: dict[str, Any] | None) -> list[str]:
        tokens = tokenize(query)
        if not tokens or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(zip(self._order, scores, strict=True), key=lambda p: (-p[1], p[0]))
        out: list[str] = []
        for doc_id, score in ranked:
            doc = self._docs[doc_id]
            if score <= 0 or not self._keep(doc):
                continue
            if flt and any(doc.metadata.get(k) != v for k, v in flt.items()):
                continue
            out.append(doc_id)
            if len(out) == POOL:
                break
        return out

    async def _finish(
        self, query: str, rankings: list[list[str]], category: str | None, top_k: int
    ) -> list[dict[str, Any]]:
        if not rankings:
            return []
        fused = reciprocal_rank_fusion(rankings)
        ceiling = len(rankings) / (RRF_K + 1)
        q_terms = set(tokenize(query))
        scored = [
            (self._rerank_score(rrf / ceiling, self._docs[i], q_terms, category), self._docs[i])
            for i, rrf in fused.items()
            if i in self._docs
        ]
        scored.sort(key=lambda p: (-p[0], p[1].id))

        evidence: list[dict[str, Any]] = []
        seen: set[str] = set()
        for score, doc in scored:
            article = doc.metadata["article_id"]
            if article not in seen:
                seen.add(article)
                evidence.append(_evidence(doc, score))
        if self._llm_rerank is not None:
            evidence = await _maybe_await(self._llm_rerank(query, evidence))
        return evidence[:top_k]

    def _coverage(self, terms: list[str], evidence: dict[str, Any]) -> tuple[int, float]:
        """(matched words, share of the query's words) found anywhere in the hit's article."""
        seen = self._article_words.get(evidence.get("article_id") or "", set())
        if not seen or not terms:
            return 0, 0.0
        # A prefix match tolerates "lockout" vs "locked" without a real stemmer (as `_check` does).
        matched = sum(1 for t in terms if any(s[:5] == t[:5] for s in seen))
        return matched, matched / len(terms)

    def _relevant(self, query: str, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only hits about the query: fewer than `top_k`, or none, when evidence is thin.

        Each kept hit is labelled "strong" or "partial" so a neighbour that only shares a few
        words is never shown as if it were as good as the answer.
        """
        terms = list(dict.fromkeys(tokenize(query)))
        if not terms:
            return evidence
        need = min(MIN_MATCHED_TERMS, len(terms))
        measured = [(e, *self._coverage(terms, e)) for e in evidence]
        best = max((cov for _, _, cov in measured), default=0.0)
        kept: list[dict[str, Any]] = []
        for e, matched, cov in measured:
            if matched < need or cov < MIN_TERM_COVERAGE or cov < best * RELATIVE_COVERAGE:
                continue
            strong = (
                cov >= STRONG_COVERAGE
                and matched >= min(STRONG_MATCHED_TERMS, len(terms))
                and cov >= best * STRONG_RELATIVE
            )
            kept.append({**e, "strength": "strong" if strong else "partial"})
        return kept

    @staticmethod
    def _rerank_score(base: float, doc: Document, q_terms: set[str], category: str | None) -> float:
        bonus = CATEGORY_BONUS if category and doc.metadata.get("category") == category else 0.0
        title = set(tokenize(doc.metadata.get("title", "")))
        overlap = len(q_terms & title) / len(q_terms) if q_terms else 0.0
        return base + bonus + TITLE_WEIGHT * overlap

    @staticmethod
    def _check(query: str, hits: list[dict[str, Any]]) -> tuple[bool, list[str]]:
        """Deterministic sufficiency: strong top hit and query terms covered by the top 3."""
        terms = list(dict.fromkeys(tokenize(query)))
        if not hits:
            return False, terms
        seen: set[str] = set()
        for h in hits[:3]:
            seen.update(tokenize(f"{h['title']} {h['snippet']}"))
        # A prefix match tolerates "lockout" vs "locked" without a real stemmer.
        covered = {t for t in terms if any(s[:5] == t[:5] for s in seen)}
        gaps = [t for t in terms if t not in covered]
        coverage = len(covered) / len(terms) if terms else 1.0
        return hits[0]["score"] >= MIN_TOP_SCORE and coverage >= MIN_COVERAGE, gaps
