"""Idempotency store backed by `resolution_actions` (FR-16, CLAUDE.md 7.4).

A key that already succeeded returns its stored result instead of acting again, across registries
and restarts. Only successful actions are stored. Needs a workflow run id, because the table links
every action to one.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.workflow import ResolutionActionRepository
from app.schemas.common import ResolutionActionStatus
from app.tools.registry import ActionMeta, ToolResult


class DbIdempotencyStore:
    requires_workflow = True

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, key: str) -> ToolResult | None:
        async with self._session_factory() as session:
            row = await ResolutionActionRepository(session).get_by_idempotency_key(key)
        if row is None or row.status != ResolutionActionStatus.executed:
            return None
        return ToolResult(
            ok=True, data=(row.result or {}).get("data"), verification=row.verification
        )

    async def set(self, key: str, result: ToolResult, meta: ActionMeta) -> None:
        async with self._session_factory() as session:
            await ResolutionActionRepository(session).create(
                ticket_id=meta.ticket_id,
                workflow_id=meta.workflow_id,
                tool=meta.tool,
                arguments=meta.args,
                status=ResolutionActionStatus.executed,
                result={"data": result.data},
                requires_approval=meta.requires_approval,
                idempotency_key=key,
                verification=result.verification,
                executed_at=datetime.now(UTC),
            )
            await session.commit()
