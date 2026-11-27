"""QA defect: retrieval padded its answer with unrelated articles to reach `top_k`.

The evidence cut-off is measured, not guessed. The ranking `score` is rank-based (an unanswerable
question still scores 0.93 to 0.96, above several correct hits), so it cannot separate relevant from
unrelated. What does separate them is how many of the query's content words the article contains:
over the 16 evaluation cases the expected article covers 0.36 to 0.83 of them, while on four
unanswerable questions no article covers more than 0.5 or more than two words. Hits are labelled
"strong" or "partial" so a neighbour that shares a few words never looks as good as the answer.
"""

from pathlib import Path

import pytest

from rag.chunking import chunk_article, load_article_files
from rag.embeddings import FakeEmbeddings
from rag.retriever import HybridRetriever, documents_from_chunks
from rag.vector_store import InMemoryVectorStore

KB = Path(__file__).resolve().parents[2] / "sample_data" / "knowledge_base"


@pytest.fixture
async def retriever():
    emb = FakeEmbeddings()
    docs = documents_from_chunks([c for a in load_article_files(KB) for c in chunk_article(a)], emb)
    store = InMemoryVectorStore()
    await store.add_documents(docs)
    return HybridRetriever(store, emb, docs)


async def test_a_well_covered_query_keeps_its_article_and_drops_the_padding(retriever):
    result = await retriever.retrieve(
        "What should I do when API requests receive HTTP 429?", top_k=5
    )
    ids = [e["article_id"] for e in result.evidence]
    assert ids[0] == "api-rate-limits"
    assert len(ids) < 5, "unrelated articles must not be added to reach top_k"
    assert "dark-mode-and-feature-requests" not in ids
    assert "account-deletion-and-data-erasure" not in ids
    assert result.sufficient


async def test_a_refund_ticket_has_one_strong_article_and_only_partial_neighbours(retriever):
    query = (
        "Refund: charged 8 seats, uses 5 "
        "We were billed for 8 seats this month but only 5 people actually use the workspace. "
        "Please refund the 3 unused seats."
    )
    evidence = (await retriever.retrieve(query, top_k=5)).evidence
    assert evidence[0]["article_id"] == "refunds-and-seat-billing"
    assert evidence[0]["strength"] == "strong"
    # Articles that share a few words (workspace, seats) may stay, but never as strong. A genuinely
    # related billing article (invoices) may be strong too, so only the off-topic ones are pinned.
    off_topic = {"external-sharing-permissions", "workspace-roles-and-permissions"}
    assert all(e["strength"] == "partial" for e in evidence if e["article_id"] in off_topic)


@pytest.mark.parametrize(
    "query",
    [
        "How do I bake sourdough bread at home?",
        "Who won the football world cup in 2018?",
        "Explain quantum entanglement to a child",
    ],
)
async def test_an_unrelated_query_returns_no_evidence_and_is_marked_insufficient(retriever, query):
    result = await retriever.retrieve(query, top_k=5)
    assert result.evidence == []
    assert result.sufficient is False


async def test_a_query_sharing_only_two_words_is_never_strong_and_is_insufficient(retriever):
    # "password" and one more word appear in the security articles; nothing answers the question.
    result = await retriever.retrieve(
        "What is the internal password of the production database?", top_k=5
    )
    assert all(e["strength"] == "partial" for e in result.evidence)
    assert result.sufficient is False


async def test_a_weakly_related_query_returns_fewer_than_top_k(retriever):
    # One real topic word ("storage") next to words the knowledge base does not use.
    result = await retriever.retrieve(
        "Is the weather nice for storage of my feelings today", top_k=5
    )
    assert len(result.evidence) < 5


async def test_a_single_word_query_is_still_answered(retriever):
    result = await retriever.retrieve("MFA", top_k=3)
    assert result.evidence and result.evidence[0]["article_id"] == "mfa-recovery"


async def test_top_k_still_caps_the_result(retriever):
    result = await retriever.retrieve("SSO login fails for the whole team", top_k=1)
    assert len(result.evidence) <= 1
