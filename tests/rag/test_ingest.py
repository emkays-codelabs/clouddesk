"""P5-4 (F5): ingest loads, chunks, embeds and indexes the knowledge base; idempotent; reindex."""

from pathlib import Path

from rag.embeddings import FakeEmbeddings
from rag.ingest import ingest
from rag.vector_store import InMemoryVectorStore

KB = Path(__file__).resolve().parents[2] / "sample_data" / "knowledge_base"


async def test_ingest_reports_15_articles_and_indexes_every_chunk():
    store = InMemoryVectorStore()

    result = await ingest(store, FakeEmbeddings(), KB)

    assert result.articles == 15
    assert result.chunks > 15
    assert await store.count() == result.chunks


async def test_a_second_ingest_leaves_the_chunk_count_unchanged():
    store = InMemoryVectorStore()
    first = await ingest(store, FakeEmbeddings(), KB)

    second = await ingest(store, FakeEmbeddings(), KB)

    assert second == first
    assert await store.count() == first.chunks


async def test_reindex_recreates_the_collection_and_drops_stale_chunks():
    store = InMemoryVectorStore()
    emb = FakeEmbeddings()
    await ingest(store, emb, KB)
    from rag.vector_store import Document

    await store.add_documents([Document("stale#0", "old", emb.embed_query("old"), {})])

    result = await ingest(store, emb, KB, recreate=True)

    assert await store.count() == result.chunks
    assert result.articles == 15
