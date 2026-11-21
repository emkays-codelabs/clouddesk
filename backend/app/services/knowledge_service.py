"""Knowledge use cases: index the knowledge base, list and read articles, search, reindex (F5).

Does: own the in-process index state (articles and embedded chunk documents), ingest into the vector
store chosen by settings, and search through `HybridRetriever` with the Redis cache adapter. Article
ids are the file slugs, so they are stable. `python -m app.services.knowledge_service` ingests and
prints article and chunk counts (`make ingest`).
Must NOT: talk HTTP, touch the database, or know which vector store is live.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.schemas.knowledge import (
    Article,
    ArticleDetail,
    Evidence,
    ReindexResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.retrieval_cache import RedisRetrievalCache
from rag.chunking import Article as SourceArticle
from rag.chunking import load_article_files
from rag.embeddings import FakeEmbeddings
from rag.ingest import IngestResult, get_vector_store, ingest, load_documents
from rag.retriever import Document, HybridRetriever

logger = logging.getLogger(__name__)

_articles: dict[str, SourceArticle] = {}
_documents: list[Document] = []


class ArticleNotFound(Exception):
    pass


def _directory() -> Path:
    return Path(get_settings().sample_data_dir) / "knowledge_base"


def _embeddings() -> FakeEmbeddings:
    return FakeEmbeddings(get_settings().embedding_dimensions)


async def _build(*, recreate: bool) -> IngestResult:
    directory, embeddings = _directory(), _embeddings()
    store = get_vector_store(get_settings())
    result = await ingest(store, embeddings, directory, recreate=recreate)
    _articles.clear()
    _articles.update({a.slug: a for a in load_article_files(directory)})
    _documents[:] = load_documents(directory, embeddings)[1]
    return result


async def index_knowledge_base() -> IngestResult:
    """Ingest (idempotent). Safe to call at every startup."""
    return await _build(recreate=False)


async def reindex() -> ReindexResponse:
    result = await _build(recreate=True)
    logger.info("knowledge reindexed", extra={"articles": result.articles, "chunks": result.chunks})
    return ReindexResponse(indexed=result.chunks)


async def _ensure_indexed() -> None:
    # The store is a process singleton; an empty one (never started, or reset) is refilled.
    if not _articles or await get_vector_store(get_settings()).count() == 0:
        await index_knowledge_base()


def _to_article(a: SourceArticle) -> Article:
    modified = datetime.fromtimestamp((_directory() / f"{a.slug}.md").stat().st_mtime, tz=UTC)
    return Article(
        id=a.slug,
        slug=a.slug,
        title=a.title,
        category=a.category,
        tags=a.tags,
        summary=a.summary,
        updated_at=modified,
    )


async def list_articles(*, search: str | None, category: str | None) -> list[Article]:
    await _ensure_indexed()
    needle = (search or "").strip().lower()
    out = []
    for a in _articles.values():
        if category and a.category != category:
            continue
        haystack = f"{a.title} {a.summary} {' '.join(a.tags)} {a.body}".lower()
        if needle and needle not in haystack:
            continue
        out.append(_to_article(a))
    return out


async def get_article(article_id: str) -> ArticleDetail:
    await _ensure_indexed()
    a = _articles.get(article_id)
    if a is None:
        raise ArticleNotFound(article_id)
    return ArticleDetail(**_to_article(a).model_dump(), content=a.body)


async def search(request: SearchRequest) -> SearchResponse:
    await _ensure_indexed()
    started = time.perf_counter()
    retriever = HybridRetriever(
        get_vector_store(get_settings()),
        _embeddings(),
        _documents,
        cache=RedisRetrievalCache(),
    )
    result = await retriever.retrieve(request.query, mode=request.mode, top_k=request.top_k)
    return SearchResponse(
        results=[Evidence(**e) for e in result.evidence],
        mode=request.mode,
        took_ms=int((time.perf_counter() - started) * 1000),
    )


if __name__ == "__main__":
    done = asyncio.run(index_knowledge_base())
    print(f"articles: {done.articles}")
    print(f"chunks: {done.chunks}")
