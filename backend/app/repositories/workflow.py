"""Workflow runs, their events, and the resolution actions they plan."""

from datetime import UTC, datetime
from typing import Any

from app.models.entities import ResolutionAction, WorkflowEvent, WorkflowRun
from app.repositories.base import ScopedRepository
from app.schemas.common import ResolutionActionStatus


class WorkflowRunRepository(ScopedRepository[WorkflowRun]):
    model = WorkflowRun

    async def create(self, **fields: Any) -> WorkflowRun:
        return await self._add(WorkflowRun(**fields))

    async def get(self, id: str) -> WorkflowRun | None:
        return await self._get(id)

    async def latest_for_ticket(self, ticket_id: str) -> WorkflowRun | None:
        stmt = (
            self._select(WorkflowRun.ticket_id == ticket_id)
            .order_by(WorkflowRun.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update(self, id: str, **fields: Any) -> WorkflowRun | None:
        return await self._update_where(id, **fields)

    async def list_recent(self, limit: int = 20) -> list[WorkflowRun]:
        stmt = self._select().order_by(WorkflowRun.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class WorkflowEventRepository(ScopedRepository[WorkflowEvent]):
    model = WorkflowEvent

    async def append(self, **fields: Any) -> WorkflowEvent:
        return await self._add(WorkflowEvent(**fields))

    async def list_for_ticket(self, ticket_id: str) -> list[WorkflowEvent]:
        stmt = self._select(WorkflowEvent.ticket_id == ticket_id).order_by(WorkflowEvent.created_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workflow(self, workflow_id: str) -> list[WorkflowEvent]:
        stmt = self._select(WorkflowEvent.workflow_id == workflow_id).order_by(
            WorkflowEvent.created_at
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ResolutionActionRepository(ScopedRepository[ResolutionAction]):
    model = ResolutionAction

    async def create(self, **fields: Any) -> ResolutionAction:
        return await self._add(ResolutionAction(**fields))

    async def list_for_ticket(self, ticket_id: str) -> list[ResolutionAction]:
        stmt = self._select(ResolutionAction.ticket_id == ticket_id).order_by(
            ResolutionAction.created_at
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_idempotency_key(self, key: str) -> ResolutionAction | None:
        result = await self.session.execute(self._select(ResolutionAction.idempotency_key == key))
        return result.scalar_one_or_none()

    async def record_result(
        self,
        id: str,
        status: ResolutionActionStatus,
        result: dict[str, Any] | None,
        verification: dict[str, Any] | None,
    ) -> ResolutionAction | None:
        return await self._update_where(
            id,
            status=status,
            result=result,
            verification=verification,
            executed_at=datetime.now(UTC),
        )
