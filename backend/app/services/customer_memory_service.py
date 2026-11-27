"""Wire `memory/` to the app: repository, core scrub and the live vector store (F4, F11, N7).

Does: build a `MemoryService` over one session so every note passes `app.core.scrub.scrub`, and
`erase_customer_memory` (rows and vectors, upstream FR-27). Notes are written as rows only; no
embeddings are passed, so the knowledge index gets no memory vectors, but erasure still deletes
any that exist. The caller commits. Must NOT: talk HTTP or hold memory rules (see `memory/`).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.scrub import scrub
from app.repositories.memory import CustomerMemoryRepository
from memory.long_term import ErasureReport, LongTermMemory
from memory.memory_service import MemoryService
from rag.ingest import get_vector_store


def build_memory_service(session: AsyncSession) -> MemoryService:
    return MemoryService(LongTermMemory(CustomerMemoryRepository(session), scrub=scrub), scrub)


async def erase_customer_memory(session: AsyncSession, customer_id: str) -> ErasureReport:
    long_term = LongTermMemory(
        CustomerMemoryRepository(session), vector_store=get_vector_store(get_settings())
    )
    return await long_term.erase(customer_id)
