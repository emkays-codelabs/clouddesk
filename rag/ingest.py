"""Load the knowledge articles, chunk them, embed them and add them to the vector store.

Does: `ingest(store, embeddings, directory, recreate=False)` returns an `IngestResult` with the
article and chunk counts. It is idempotent: chunk ids are stable (`{slug}#{n}`) and the store
replaces a document with the same id, so a second run leaves the count unchanged. `recreate=True`
clears the store first (reindex), which also drops chunks of articles that no longer exist.
`load_documents` returns the same embedded documents for the retriever.
Must NOT: know about tickets, customers or workflows, touch the database, import `app.*`, or know
which vector store is live.
"""

from dataclasses import dataclass
from pathlib import Path

from rag.chunking import chunk_article, load_article_files
from rag.embeddings import Embeddings
from rag.retriever import documents_from_chunks
from rag.vector_store import Document, VectorStoreService, get_vector_store

__all__ = ["IngestResult", "get_vector_store", "ingest", "load_documents"]


@dataclass(frozen=True)
class IngestResult:
    articles: int
    chunks: int


def load_documents(directory: Path | str, embeddings: Embeddings) -> tuple[int, list[Document]]:
    """(article count, embedded chunk documents) for every article in `directory`."""
    articles = load_article_files(directory)
    chunks = [c for a in articles for c in chunk_article(a)]
    return len(articles), documents_from_chunks(chunks, embeddings)


async def ingest(
    store: VectorStoreService,
    embeddings: Embeddings,
    directory: Path | str,
    *,
    recreate: bool = False,
) -> IngestResult:
    articles, documents = load_documents(directory, embeddings)
    if recreate:
        await store.clear()
    await store.add_documents(documents)
    return IngestResult(articles=articles, chunks=len(documents))
