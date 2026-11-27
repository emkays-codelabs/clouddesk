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
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.injection_guard import drop_injected_chunks
from app.core.llm import EURON_BASE_URL
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
from rag.embeddings import (
    EURON_EMBEDDING_MODEL,
    EmbeddingError,
    Embeddings,
    EuronEmbeddings,
    FakeEmbeddings,
)
from rag.ingest import IngestResult, get_vector_store, ingest, load_documents
from rag.retriever import Document, HybridRetriever

logger = logging.getLogger(__name__)

# Retrieved chunks are untrusted too: a chunk carrying an instruction never reaches evidence (N4).
CHUNK_FILTER = drop_injected_chunks

_articles: dict[str, SourceArticle] = {}
_documents: list[Document] = []


class ArticleNotFound(Exception):
    pass


def _directory() -> Path:
    return Path(get_settings().sample_data_dir) / "knowledge_base"


@lru_cache(maxsize=4)
def _euron(api_key: str, base_url: str, model: str, dimensions: int) -> EuronEmbeddings:
    return EuronEmbeddings(api_key, base_url, model=model, dimensions=dimensions)


def build_embeddings(settings: Settings) -> Embeddings:
    """The embeddings for `EMBEDDING_PROVIDER` (P9-10). The only place that reads those settings.

    `euron` takes its base URL from `EMBEDDING_BASE_URL`, else the LLM base URL, else Euron's own,
    and its key from `LLM_API_KEY`. Switching providers changes the vectors: reindex afterwards.
    """
    provider = settings.embedding_provider.strip().lower()
    if provider == "fake":
        return FakeEmbeddings(settings.embedding_dimensions)
    if provider == "euron":
        key = settings.llm_api_key.get_secret_value()
        if not key:
            raise EmbeddingError("LLM_API_KEY is not set for the euron embeddings provider.")
        base_url = settings.embedding_base_url or settings.llm_base_url or EURON_BASE_URL
        model = settings.embedding_model or EURON_EMBEDDING_MODEL
        return _euron(key, base_url, model, settings.embedding_dimensions)
    raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER {provider!r}; use fake or euron.")


def _embeddings() -> Embeddings:
    return build_embeddings(get_settings())


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
        chunk_filter=CHUNK_FILTER,
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
