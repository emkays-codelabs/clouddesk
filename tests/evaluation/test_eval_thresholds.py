"""P14-1 (F2, F5, F8, F10): the evaluation thresholds that fail the build (CLAUDE.md 13).

Every ticket case in `datasets/eval_cases.json` runs through the real workflow API on the fake
model; the text-only cases go through the rules and the retriever. The metrics are computed over the
run results, and each one must clear its floor.
"""

import json
from pathlib import Path

import pytest

from agents.rules import matching_escalation_rules, rule_category
from rag.chunking import chunk_article, load_article_files
from rag.embeddings import FakeEmbeddings
from rag.retriever import HybridRetriever, documents_from_chunks
from rag.vector_store import InMemoryVectorStore

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "datasets" / "eval_cases.json").read_text("utf-8"))
TICKET_CASES = [c for c in CASES if "ticket" in c]
TICKETS = {
    t["ticket_number"]: t
    for t in json.loads((ROOT / "sample_data" / "tickets.json").read_text("utf-8"))
}
KB = ROOT / "sample_data" / "knowledge_base"

THRESHOLDS = {
    "classification": 0.80,
    "hit_rate_at_3": 0.75,
    "escalation": 0.90,
    "citation": 0.90,
    "grounding": 0.90,
}


def _text(case) -> str:
    if "ticket" in case:
        t = TICKETS[case["ticket"]]
        return f"{t['subject']}\n{t['body']}"
    return case["text"]


@pytest.fixture
def runs(fresh_db, client, agent_headers):
    """Run each ticket case once; return {case id: final workflow state}."""
    from app.services import workflow_service

    workflow_service.reset_checkpointer()
    results = {}
    for case in TICKET_CASES:
        page = client.get(
            "/api/v1/tickets", headers=agent_headers, params={"search": case["ticket"]}
        ).json()
        ticket_id = next(t["id"] for t in page["items"] if t["ticket_number"] == case["ticket"])
        response = client.post(f"/api/v1/tickets/{ticket_id}/run", headers=agent_headers)
        assert response.status_code == 202
        results[case["id"]] = client.get(
            f"/api/v1/tickets/{ticket_id}/workflow", headers=agent_headers
        ).json()
    yield results
    workflow_service.reset_checkpointer()


async def _hit_rate() -> float:
    emb = FakeEmbeddings()
    chunks = [c for a in load_article_files(KB) for c in chunk_article(a)]
    docs = documents_from_chunks(chunks, emb)
    store = InMemoryVectorStore()
    await store.add_documents(docs)
    retriever = HybridRetriever(store, emb, docs)
    hits = 0
    for case in CASES:
        result = await retriever.retrieve(_text(case), top_k=3)
        hits += case["expected_article"] in [e["article_id"] for e in result.evidence]
    return hits / len(CASES)


def test_classification_accuracy(runs):
    right = 0
    for case in TICKET_CASES:
        state = runs[case["id"]]
        got = (state.get("classification") or {}).get("category")
        right += got == case["expected_category"]
    for case in CASES:
        if "text" in case:
            right += rule_category(_text(case)) == case["expected_category"]
    total = len(TICKET_CASES) + sum("text" in c for c in CASES)
    assert right / total >= THRESHOLDS["classification"], right / total


async def test_retrieval_hit_rate_at_3():
    assert await _hit_rate() >= THRESHOLDS["hit_rate_at_3"]


def test_escalation_correctness(runs):
    right = 0
    for case in TICKET_CASES:
        state = runs[case["id"]]
        right += bool(state.get("escalation_required")) == case["expected_escalation"]
    for case in CASES:
        if "text" in case:
            matched = bool(matching_escalation_rules(_text(case), case.get("plan_name", "pro")))
            right += matched == case["expected_escalation"]
    total = len(CASES)
    assert right / total >= THRESHOLDS["escalation"], right / total


def test_citation_rate(runs):
    replies = [s for s in runs.values() if s.get("final_response") and s.get("retrieved_docs")]
    assert replies, "no run produced a customer reply"
    cited = sum(
        any(doc["title"] in s["final_response"] for doc in s["retrieved_docs"]) for s in replies
    )
    assert cited / len(replies) >= THRESHOLDS["citation"], cited / len(replies)


def test_grounding_rate(runs):
    replies = [s for s in runs.values() if s.get("final_response") and s.get("diagnosis")]
    assert replies, "no run produced a diagnosis and a reply"
    grounded = 0
    for s in replies:
        steps = s["diagnosis"].get("steps") or []
        text = s["final_response"].lower()
        present = sum(1 for step in steps if str(step).lower()[:40] in text)
        grounded += (present / len(steps) if steps else 1.0) >= 0.5
    assert grounded / len(replies) >= THRESHOLDS["grounding"], grounded / len(replies)
