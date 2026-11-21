"""Store document vectors and search them, behind one protocol.

Does: define `Document`, `SearchHit`, the `VectorStoreService` protocol (add_documents, search,
delete, count, clear, health), `InMemoryVectorStore` (cosine similarity), `QdrantVectorStore`
(imports `qdrant_client` lazily, only when first used) and `get_vector_store(settings)`, which picks
one from `settings.vector_store`. Callers elsewhere only ever see the protocol.
Must NOT: embed text, know about tickets, customers or workflows, import `app.repositories` /
`app.models`, or import `qdrant_client` at module level.
"""

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Document:
    id: str
    text: str
    vector: list[float]
    # article_id, title, category, source, heading
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    document: Document
    score: float


class VectorStoreService(Protocol):
    async def add_documents(self, documents: list[Document]) -> None: ...

    async def search(
        self, vector: list[float], top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]: ...

    async def delete(self, ids: list[str]) -> None: ...

    async def count(self) -> int: ...

    async def clear(self) -> None: ...

    async def health(self) -> bool: ...


def _matches(doc: Document, filters: dict[str, Any] | None) -> bool:
    return all(doc.metadata.get(k) == v for k, v in (filters or {}).items())


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    async def add_documents(self, documents: list[Document]) -> None:
        for doc in documents:
            self._docs[doc.id] = doc

    async def search(
        self, vector: list[float], top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        hits = [
            SearchHit(d, _cosine(vector, d.vector))
            for d in self._docs.values()
            if _matches(d, filters)
        ]
        return sorted(hits, key=lambda h: (-h.score, h.document.id))[:top_k]

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            self._docs.pop(id_, None)

    async def count(self) -> int:
        return len(self._docs)

    async def clear(self) -> None:
        self._docs.clear()

    async def health(self) -> bool:
        return True


def _point_id(doc_id: str) -> str:
    # Qdrant point ids must be UUIDs or ints; derive a stable UUID from the chunk id.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id))


class QdrantVectorStore:
    def __init__(self, url: str, api_key: str, collection: str, dimensions: int) -> None:
        self._url, self._api_key = url, api_key
        self._collection, self._dimensions = collection, dimensions
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from qdrant_client import QdrantClient  # lazy: offline runs never need it

            self._client = QdrantClient(url=self._url, api_key=self._api_key or None)
        return self._client

    def _ensure_collection(self) -> None:
        from qdrant_client import models

        client = self._get_client()
        if not client.collection_exists(self._collection):
            client.create_collection(
                self._collection,
                vectors_config=models.VectorParams(
                    size=self._dimensions, distance=models.Distance.COSINE
                ),
            )

    async def add_documents(self, documents: list[Document]) -> None:
        from qdrant_client import models

        self._ensure_collection()
        points = [
            models.PointStruct(
                id=_point_id(d.id),
                vector=d.vector,
                payload={**d.metadata, "doc_id": d.id, "text": d.text},
            )
            for d in documents
        ]
        self._get_client().upsert(self._collection, points=points)

    async def search(
        self, vector: list[float], top_k: int = 5, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        from qdrant_client import models

        flt = None
        if filters:
            flt = models.Filter(
                must=[
                    models.FieldCondition(key=k, match=models.MatchValue(value=v))
                    for k, v in filters.items()
                ]
            )
        res = self._get_client().query_points(
            self._collection, query=vector, limit=top_k, query_filter=flt, with_payload=True
        )
        hits = []
        for p in res.points:
            payload = dict(p.payload or {})
            doc_id, text = payload.pop("doc_id"), payload.pop("text", "")
            hits.append(SearchHit(Document(doc_id, text, [], payload), float(p.score)))
        return hits

    async def delete(self, ids: list[str]) -> None:
        from qdrant_client import models

        self._get_client().delete(
            self._collection,
            points_selector=models.PointIdsList(points=[_point_id(i) for i in ids]),
        )

    async def count(self) -> int:
        client = self._get_client()
        if not client.collection_exists(self._collection):
            return 0
        return int(client.count(self._collection, exact=True).count)

    async def clear(self) -> None:
        client = self._get_client()
        if client.collection_exists(self._collection):
            client.delete_collection(self._collection)  # recreated on the next write

    async def health(self) -> bool:
        try:
            self._get_client().get_collections()
            return True
        except Exception:
            return False


_cache: VectorStoreService | None = None


def get_vector_store(settings: Any, *, fresh: bool = False) -> VectorStoreService:
    """Pick the store named by `settings.vector_store`; cached so callers share one index."""
    global _cache
    if _cache is None or fresh:
        if settings.vector_store == "qdrant":
            _cache = QdrantVectorStore(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key.get_secret_value(),
                collection=settings.qdrant_collection,
                dimensions=settings.embedding_dimensions,
            )
        else:
            _cache = InMemoryVectorStore()
    return _cache


def reset_vector_store() -> None:
    """Drop the cached store (tests, reindex)."""
    global _cache
    _cache = None
