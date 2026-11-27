"""QA defect: evidence snippets were cut mid-word ("...The refundable amount is the numb")."""

from rag.retriever import SNIPPET_CHARS, snippet_of


def test_short_text_is_returned_whole_without_an_ellipsis():
    assert snippet_of("A short sentence.", 240) == "A short sentence."


def test_it_never_cuts_inside_a_word():
    text = "word " * 100  # 500 characters
    out = snippet_of(text, 50)
    assert out.endswith("…")
    body = out[:-1]
    assert body == body.rstrip() and set(body.split()) == {"word"}


def test_it_prefers_the_last_sentence_boundary():
    text = (
        "First sentence here. Second sentence is a little longer than the first one. "
        "Third one follows."
    )
    out = snippet_of(text, 80)
    assert out == "First sentence here. Second sentence is a little longer than the first one.…"
    assert "Third" not in out


def test_a_boundary_too_early_is_ignored_in_favour_of_a_word_boundary():
    text = "Hi. " + "alpha beta gamma delta epsilon " * 10
    out = snippet_of(text, 80)
    assert len(out) > 40  # did not stop after "Hi."
    assert out.endswith("…")


def test_trailing_punctuation_is_not_left_dangling_before_the_ellipsis():
    out = snippet_of("alpha, beta, gamma, delta, epsilon, zeta, eta, theta", 24)
    assert not out.rstrip("…").endswith((",", ";", ":"))


def test_one_very_long_word_is_hard_cut_with_an_ellipsis():
    out = snippet_of("x" * 500, 40)
    assert out == "x" * 40 + "…"


def test_the_default_limit_is_the_documented_snippet_length():
    assert SNIPPET_CHARS == 240
    assert len(snippet_of("lorem ipsum dolor sit amet " * 40, SNIPPET_CHARS)) <= SNIPPET_CHARS + 1


async def test_evidence_keeps_the_full_passage_behind_a_short_snippet():
    from pathlib import Path

    from rag.chunking import chunk_article, load_article_files
    from rag.embeddings import FakeEmbeddings
    from rag.retriever import HybridRetriever, documents_from_chunks
    from rag.vector_store import InMemoryVectorStore

    kb = Path(__file__).resolve().parents[2] / "sample_data" / "knowledge_base"
    emb = FakeEmbeddings()
    docs = documents_from_chunks([c for a in load_article_files(kb) for c in chunk_article(a)], emb)
    store = InMemoryVectorStore()
    await store.add_documents(docs)
    result = await HybridRetriever(store, emb, docs).retrieve(
        "Refund: charged 8 seats, uses 5. Please refund the 3 unused seats.", top_k=3
    )
    first = result.evidence[0]
    assert first["passage"].startswith(first["snippet"].rstrip("…").rstrip())
    assert len(first["passage"]) >= len(first["snippet"].rstrip("…"))
    assert not first["snippet"].rstrip("…").endswith(" ")
