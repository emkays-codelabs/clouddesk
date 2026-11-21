"""P5-3 (F5, F6): hybrid retriever - modes, RRF, rerank, filter, cache, sufficiency, hit-rate@3."""

from pathlib import Path

import fakeredis
import pytest

from app.services.retrieval_cache import RedisRetrievalCache
from rag.chunking import chunk_article, load_article_files
from rag.embeddings import FakeEmbeddings
from rag.retriever import (
    HybridRetriever,
    documents_from_chunks,
    reciprocal_rank_fusion,
    rewrite_query,
)
from rag.vector_store import InMemoryVectorStore

KB = Path(__file__).resolve().parents[2] / "sample_data" / "knowledge_base"

# Queries drawn from the demo tickets CD-1001..CD-1012 (subject and body wording).
CASES = [
    ("SSO login fails for whole team, bounced back to the login page", "sso-login-failures"),
    ("Refund: charged 8 seats, uses 5, refund the unused seats", "refunds-and-seat-billing"),
    ("API 429 on nightly sync, what limit are we hitting", "api-rate-limits"),
    ("Uploads fail: storage quota exceeded", "storage-quota"),
    ("Suspicious logins from countries, account may be compromised", "suspicious-logins-security"),
    ("Files disappeared from folder, can you restore the files", "data-loss-and-restore"),
    ("Can't share folder externally with an outside agency", "external-sharing-permissions"),
    ("Slack integration stopped posting file updates", "slack-integration"),
    ("Delete legacy workspace and permanently erase all data", "account-deletion-and-data-erasure"),
    ("Unauthorized charge, disputing it with our bank", "payment-disputes"),
    ("Locked out after too many MFA attempts, changed phones", "mfa-recovery"),
]


@pytest.fixture(scope="module")
def index():
    emb = FakeEmbeddings()
    chunks = [c for a in load_article_files(KB) for c in chunk_article(a)]
    docs = documents_from_chunks(chunks, emb)
    store = InMemoryVectorStore()
    return emb, store, docs


@pytest.fixture
async def retriever(index):
    emb, store, docs = index
    await store.add_documents(docs)
    return HybridRetriever(store, emb, docs)


def _ids(result):
    return [e["article_id"] for e in result.evidence]


async def test_hit_rate_at_3_over_demo_queries(retriever):
    hits = 0
    for query, expected in CASES:
        result = await retriever.retrieve(query, top_k=3)
        hits += expected in _ids(result)
    assert hits / len(CASES) >= 0.75
    assert hits == len(CASES)


async def test_evidence_shape(retriever):
    result = await retriever.retrieve("Locked out after MFA attempts", top_k=3)
    e = result.evidence[0]
    assert set(e) == {"id", "title", "source", "snippet", "score", "url", "article_id"}
    assert e["source"].startswith(f"kb://{e['article_id']}#")
    assert e["url"] == f"/knowledge/{e['article_id']}"
    assert 0 < e["score"]


@pytest.mark.parametrize("mode", ["hybrid", "semantic", "keyword"])
async def test_each_mode_finds_the_article(retriever, mode):
    result = await retriever.retrieve("storage quota exceeded uploads fail", mode=mode, top_k=3)
    assert "storage-quota" in _ids(result)


async def test_modes_use_different_rankings(index):
    emb, store, docs = index
    await store.add_documents(docs)
    r = HybridRetriever(store, emb, docs)
    kw = await r._rank(["quota exceeded"], "keyword", None)
    sem = await r._rank(["quota exceeded"], "semantic", None)
    both = await r._rank(["quota exceeded"], "hybrid", None)
    assert len(kw) == 1 and len(sem) == 1 and len(both) == 2


async def test_one_hit_per_article(retriever):
    result = await retriever.retrieve("MFA recovery codes lockout", top_k=10)
    ids = _ids(result)
    assert len(ids) == len(set(ids))


async def test_category_filter(retriever):
    result = await retriever.retrieve("refund charge account", category="billing", top_k=10)
    assert result.evidence
    by_article = {a.slug: a.category for a in load_article_files(KB)}
    assert {by_article[i] for i in _ids(result)} == {"billing"}


async def test_category_boost_reorders_when_soft(retriever):
    query = "account access problem"
    plain = await retriever.retrieve(query, top_k=15)
    boosted = await retriever.retrieve(query, category="security", top_k=15, strict_category=False)
    top_plain = plain.evidence[0]["score"]
    sec = next(e for e in boosted.evidence if e["article_id"] == "suspicious-logins-security")
    base = next(e for e in plain.evidence if e["article_id"] == "suspicious-logins-security")
    assert sec["score"] == pytest.approx(base["score"] + 0.15, abs=1e-3)
    assert top_plain > 0


def test_rrf_math():
    scores = reciprocal_rank_fusion([["a", "b"], ["b", "c"]])
    assert scores["a"] == pytest.approx(1 / 61)
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["c"] == pytest.approx(1 / 62)
    assert max(scores, key=scores.get) == "b"


async def test_title_overlap_rerank_lifts_matching_title(index):
    emb, store, docs = index
    await store.add_documents(docs)
    r = HybridRetriever(store, emb, docs)
    result = await r.retrieve("payment disputes", top_k=3)
    assert result.evidence[0]["article_id"] == "payment-disputes"
    # Title overlap adds to the score, so a perfect title match exceeds the fused base of 1.0.
    assert result.evidence[0]["score"] > 1.0


def test_rewrite_gives_one_to_three_subqueries():
    subs = rewrite_query("Why can't I upload files to the storage quota?")
    assert 1 <= len(subs) <= 3 and subs[0].startswith("Why")
    assert rewrite_query("quota") == ["quota"]


async def test_rewriter_hook_adds_a_subquery(index):
    emb, store, docs = index
    await store.add_documents(docs)
    seen = []

    def rewriter(q):
        seen.append(q)
        return ["authenticator app recovery"]

    r = HybridRetriever(store, emb, docs, rewriter=rewriter)
    await r.retrieve("locked out", top_k=3)
    assert seen == ["locked out"]


async def test_chunk_filter_drops_chunks(index):
    emb, store, docs = index
    await store.add_documents(docs)
    r = HybridRetriever(
        store, emb, docs, chunk_filter=lambda d: d.metadata["article_id"] != "storage-quota"
    )
    result = await r.retrieve("storage quota exceeded uploads fail", top_k=10)
    assert "storage-quota" not in _ids(result)


async def test_llm_rerank_hook_reorders(index):
    emb, store, docs = index
    await store.add_documents(docs)

    async def reverse(query, hits):
        return list(reversed(hits))

    plain = HybridRetriever(store, emb, docs)
    hooked = HybridRetriever(store, emb, docs, llm_rerank=reverse)
    a = _ids(await plain.retrieve("MFA lockout recovery", top_k=50))
    b = _ids(await hooked.retrieve("MFA lockout recovery", top_k=50))
    assert len(a) >= 3
    assert b == list(reversed(a))


async def test_cache_hit_skips_recompute_and_key_shape(index):
    emb, store, docs = index
    await store.add_documents(docs)
    redis = fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer(), decode_responses=True)
    r = HybridRetriever(store, emb, docs, cache=RedisRetrievalCache(redis))
    first = await r.retrieve("MFA lockout", category="login_issue", top_k=3)
    assert r.search_calls >= 1
    calls = r.search_calls
    second = await r.retrieve("MFA lockout", category="login_issue", top_k=3)
    assert r.search_calls == calls
    assert second.cached and not first.cached
    assert second.evidence == first.evidence
    key = "rag:hybrid:login_issue:3:MFA lockout"
    assert await redis.exists(key) == 1
    assert 0 < await redis.ttl(key) <= 300


async def test_insufficient_evidence_retries_exactly_once(retriever):
    result = await retriever.retrieve("zeppelin banana quantum", top_k=3)
    assert result.passes == 2
    assert retriever.search_calls == 2
    assert not result.sufficient


async def test_sufficient_evidence_does_not_retry(retriever):
    result = await retriever.retrieve("payment disputes", top_k=3)
    assert result.sufficient and result.passes == 1
    assert retriever.search_calls == 1
