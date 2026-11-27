"""Long-term customer memory (CLAUDE.md 7.5, F4, F11) over the `customer_memory` repository.

Does: `LongTermMemory(repo, vector_store=None, embeddings=None, scrub=None)` remembers a fact only
at confidence >= 0.7 (lower is discarded, not stored), skips an exact duplicate of the same type for
the same customer, recalls at most 10 notes newest first, and erases a customer's rows and their
vectors together (upstream FR-27). Notes are permanent: there is no expiry. The repository (and so
the tenant filter) is an argument; the caller owns the transaction commit.
Must NOT: import `backend/app`, write SQL, name a tenant, or store text the scrub hook has not seen.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from rag.embeddings import Embeddings

# Re-exported by the retriever so memory/ never names a concrete store module.
from rag.retriever import Document, VectorStoreService

MEMORY_TYPES = ("preference", "past_issue", "troubleshooting", "note")
CONFIDENCE_FLOOR = 0.7
MAX_RECALL = 10


class MemoryRepository(Protocol):
    async def list_for_customer(self, customer_id: str, limit: int = 10) -> list[Any]: ...
    async def exists(self, customer_id: str, memory_type: Any, content: str) -> bool: ...
    async def add(self, **fields: Any) -> Any: ...
    async def ids_for_customer(self, customer_id: str) -> list[str]: ...
    async def delete_for_customer(self, customer_id: str) -> int: ...


@dataclass(frozen=True)
class Note:
    id: str
    customer_id: str
    memory_type: str
    content: str
    confidence: float | None
    source_ticket_id: str | None


@dataclass(frozen=True)
class ErasureReport:
    rows: int
    vectors: int


def _note(row: Any) -> Note:
    return Note(
        id=row.id,
        customer_id=row.customer_id,
        memory_type=str(getattr(row.memory_type, "value", row.memory_type)),
        content=row.content,
        confidence=row.confidence,
        source_ticket_id=row.source_ticket_id,
    )


class LongTermMemory:
    def __init__(
        self,
        repo: MemoryRepository,
        vector_store: VectorStoreService | None = None,
        embeddings: Embeddings | None = None,
        scrub: Callable[[str], str] | None = None,
    ) -> None:
        self._repo = repo
        self._vectors = vector_store
        self._embeddings = embeddings
        self._scrub = scrub

    async def remember(
        self,
        customer_id: str,
        memory_type: str,
        content: str,
        confidence: float = 1.0,
        source_ticket_id: str | None = None,
    ) -> Note | None:
        """Store the fact and return it; None when it is below the floor, empty or a duplicate."""
        if memory_type not in MEMORY_TYPES:
            raise ValueError(f"unknown memory type: {memory_type!r}")
        if confidence < CONFIDENCE_FLOOR:
            return None
        text = (self._scrub(content) if self._scrub else content).strip()
        if not text or await self._repo.exists(customer_id, memory_type, text):
            return None
        row = await self._repo.add(
            customer_id=customer_id,
            memory_type=memory_type,
            content=text,
            confidence=confidence,
            source_ticket_id=source_ticket_id,
        )
        if self._vectors is not None and self._embeddings is not None:
            await self._vectors.add_documents(
                [
                    Document(
                        id=row.id,
                        text=text,
                        vector=self._embeddings.embed_documents([text])[0],
                        metadata={"customer_id": customer_id, "kind": "customer_memory"},
                    )
                ]
            )
        return _note(row)

    async def recall(self, customer_id: str, limit: int = MAX_RECALL) -> list[Note]:
        rows = await self._repo.list_for_customer(customer_id, min(limit, MAX_RECALL))
        return [_note(r) for r in rows]

    async def erase(self, customer_id: str) -> ErasureReport:
        """Delete every row and every vector for the customer, vectors first so none is orphaned."""
        ids = await self._repo.ids_for_customer(customer_id)
        if ids and self._vectors is not None:
            await self._vectors.delete(ids)
        rows = await self._repo.delete_for_customer(customer_id)
        return ErasureReport(rows=rows, vectors=len(ids) if self._vectors is not None else 0)
