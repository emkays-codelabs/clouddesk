"""The workflow tracer (F13, CLAUDE.md 16): every node, tool call and model call becomes an event.

Does: `WorkflowTracer` appends `workflow_events` rows (`node_started`, `node_completed`,
`tool_called`, `llm_called`, `approval_requested`, `approval_resolved`, `error`,
`workflow_completed`) with duration, token counts and cost. Each event is written in its own short
session and committed at once, so a failure elsewhere never loses the trail.
Must NOT: raise (telemetry must never break a run: every failure is logged and swallowed), store a
raw prompt, a model's hidden reasoning, a secret or another customer's data, or import `agents/`.
"""

import logging
import time
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.scrub import scrub
from app.repositories.workflow import WorkflowEventRepository
from app.schemas.common import WorkflowEventType

logger = logging.getLogger(__name__)


class _ToolCall(Protocol):
    name: str
    ok: bool
    error: str | None
    duration_ms: int


def _clean(value: Any) -> Any:
    """Scrub strings so a secret in a payload never reaches the events table."""
    if isinstance(value, str):
        return scrub(value)[:500]
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value][:20]
    return value


class WorkflowTracer:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        workflow_id: str,
        ticket_id: str,
    ) -> None:
        self._session_factory = session_factory
        self.workflow_id = workflow_id
        self.ticket_id = ticket_id

    async def event(
        self,
        event_type: WorkflowEventType,
        *,
        node: str | None = None,
        tool: str | None = None,
        message: str = "",
        duration_ms: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            async with self._session_factory() as session:
                await WorkflowEventRepository(session).append(
                    workflow_id=self.workflow_id,
                    ticket_id=self.ticket_id,
                    event_type=event_type,
                    node=node,
                    tool=tool,
                    message=scrub(message)[:500],
                    duration_ms=duration_ms,
                    payload=_clean(payload or {}),
                )
                await session.commit()
        except Exception:  # noqa: BLE001 - telemetry must never break a run
            logger.warning("workflow event not recorded", exc_info=True)

    @asynccontextmanager
    async def node(self, name: str) -> AsyncIterator[None]:
        """`node_started` on entry, `node_completed` (with duration) on exit, `error` on failure."""
        started = time.perf_counter()
        await self.event(WorkflowEventType.node_started, node=name, message=f"{name} started")
        try:
            yield
        except Exception as exc:
            ms = int((time.perf_counter() - started) * 1000)
            await self.event(
                WorkflowEventType.error,
                node=name,
                message=f"{name} failed: {type(exc).__name__}",
                duration_ms=ms,
                payload={"error_type": type(exc).__name__},
            )
            raise
        ms = int((time.perf_counter() - started) * 1000)
        await self.event(
            WorkflowEventType.node_completed,
            node=name,
            message=f"{name} completed",
            duration_ms=ms,
        )

    async def tool_calls(self, node: str, calls: Iterable[_ToolCall]) -> None:
        for call in calls:
            await self.event(
                WorkflowEventType.tool_called,
                node=node,
                tool=call.name,
                message=f"{call.name} {'ok' if call.ok else 'failed'}",
                duration_ms=call.duration_ms,
                payload={"ok": call.ok, "error": call.error},
            )

    async def llm(self, node: str, usage: dict[str, Any], ms: int, purpose: str) -> None:
        """One model call: tokens and an estimated cost, never the prompt or the reply text."""
        if not usage.get("total_tokens") and not usage.get("estimated_cost_usd"):
            return
        await self.event(
            WorkflowEventType.llm_called,
            node=node,
            message=purpose,
            duration_ms=ms,
            payload={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "estimated_cost_usd": usage.get("estimated_cost_usd", 0.0),
                "cost_basis": usage.get("cost_basis", "none"),
            },
        )
