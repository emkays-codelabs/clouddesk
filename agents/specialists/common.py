"""Shared plumbing for the specialists: tool-call records, timing and the registry call."""

import time
from dataclasses import dataclass, field
from typing import Any

from app.tools.registry import ToolRegistry


@dataclass
class ToolCallRecord:
    """One tool call, in the shape `record_tool_calls` will turn into a `tool_called` event."""

    name: str
    args: dict[str, Any]
    ok: bool
    error: str | None = None
    duration_ms: int = 0
    data: Any = field(default=None, repr=False)


async def call_tool(
    registry: ToolRegistry,
    calls: list[ToolCallRecord],
    name: str,
    args: dict[str, Any],
    **execute_kwargs: Any,
) -> ToolCallRecord:
    """Run a tool through the registry and append its record to `calls`.

    `execute_kwargs` (ticket_id, workflow_id, approved, trusted_values) reach `registry.execute`.
    """
    started = time.perf_counter()
    result = await registry.execute(name, args, **execute_kwargs)
    record = ToolCallRecord(
        name=name,
        args=args,
        ok=result.ok,
        error=result.error,
        duration_ms=int((time.perf_counter() - started) * 1000),
        data=result.data,
    )
    calls.append(record)
    return record


def ticket_text(subject: str, body: str) -> str:
    """The text the rules and the model read: subject, then body."""
    return f"{subject}\n{body}".strip()


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
