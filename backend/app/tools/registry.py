"""ToolRegistry: the only way a tool runs (F9, CLAUDE.md 7.4).

`execute` never raises. Order of checks: unknown or unapproved, provenance, workflow id (for
tools that are recorded), idempotency, run under a timeout. A tool may return `Verified` to hand
back the read-back of its own write (FR-17); a failed read-back makes the result `ok=False`.
Failed results are never stored, so a retry can succeed.
"""

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.tools.policy import ToolPolicy, validate_provenance

ToolFn = Callable[..., Awaitable[Any]]


class ToolResult(BaseModel):
    ok: bool
    data: Any = None
    error: str | None = None
    idempotent: bool = False  # True when the stored result of an earlier call was returned
    verification: dict[str, Any] | None = None  # the read-back of a write (FR-17)


class Verified(BaseModel):
    """What a write tool returns: its result plus the read-back that proves the write."""

    data: Any
    verification: dict[str, Any]


class ActionMeta(BaseModel):
    """What the store needs to record an action beside its key."""

    ticket_id: str
    workflow_id: str
    tool: str
    args: dict[str, Any]
    requires_approval: bool


def stable_hash(args: Mapping[str, Any]) -> str:
    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class IdempotencyStore(Protocol):
    requires_workflow: bool

    async def get(self, key: str) -> ToolResult | None: ...
    async def set(self, key: str, result: ToolResult, meta: ActionMeta) -> None: ...


class InMemoryIdempotencyStore:
    requires_workflow = False

    def __init__(self) -> None:
        self._items: dict[str, ToolResult] = {}

    async def get(self, key: str) -> ToolResult | None:
        return self._items.get(key)

    async def set(self, key: str, result: ToolResult, meta: ActionMeta) -> None:
        self._items[key] = result


@dataclass
class _Registered:
    fn: ToolFn
    description: str
    provenance_fields: frozenset[str]
    idempotent: bool = True


class ToolRegistry:
    def __init__(
        self, settings: Settings | None = None, store: IdempotencyStore | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._policy = ToolPolicy(self._settings)
        self._store: IdempotencyStore = store or InMemoryIdempotencyStore()
        self._tools: dict[str, _Registered] = {}

    def register(
        self,
        tool: ToolFn,
        *,
        name: str | None = None,
        provenance_fields: Iterable[str] | None = None,
        idempotent: bool = True,
    ) -> None:
        tool_name = name or tool.__name__
        fields = (
            frozenset(provenance_fields)
            if provenance_fields is not None
            else self._policy.provenance_fields(tool_name)
        )
        self._tools[tool_name] = _Registered(tool, (tool.__doc__ or "").strip(), fields, idempotent)

    def describe(self, name: str) -> str:
        return self._tools[name].description

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": n,
                "description": t.description,
                "requires_approval": self._policy.requires_approval(n),
            }
            for n, t in self._tools.items()
        ]

    async def execute(
        self,
        name: str,
        args: Mapping[str, Any],
        approved: bool = False,
        *,
        ticket_id: str = "",
        workflow_id: str = "",
        trusted_values: Iterable[Any] | None = None,
    ) -> ToolResult:
        try:
            return await self._execute(name, args, approved, ticket_id, workflow_id, trusted_values)
        except Exception as exc:  # tool failures must never crash the graph
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")

    async def _execute(
        self,
        name: str,
        args: Mapping[str, Any],
        approved: bool,
        ticket_id: str,
        workflow_id: str,
        trusted_values: Iterable[Any] | None,
    ) -> ToolResult:
        requires_approval = self._policy.requires_approval(name, args)
        if requires_approval and not approved:
            return ToolResult(ok=False, error="approval_required")
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error="unknown_tool")

        if tool.provenance_fields:
            bad = validate_provenance(args, trusted_values or (), tool.provenance_fields)
            if bad:
                return ToolResult(ok=False, error="provenance_failed")

        if tool.idempotent and self._store.requires_workflow and not workflow_id:
            return ToolResult(ok=False, error="workflow_id_required")

        key = f"{ticket_id}:{name}:{stable_hash(args)}"
        stored = await self._store.get(key) if tool.idempotent else None
        if stored is not None and stored.ok:
            return stored.model_copy(update={"idempotent": True})

        try:
            out = await asyncio.wait_for(
                tool.fn(**args), timeout=self._settings.tool_timeout_seconds
            )
        except TimeoutError:
            return ToolResult(ok=False, error="timeout")
        except Exception as exc:
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")

        if isinstance(out, Verified):
            if not out.verification.get("verified"):
                return ToolResult(
                    ok=False,
                    data=out.data,
                    error="verification_failed",
                    verification=out.verification,
                )
            result = ToolResult(ok=True, data=out.data, verification=out.verification)
        else:
            result = ToolResult(ok=True, data=out)
        if tool.idempotent:
            meta = ActionMeta(
                ticket_id=ticket_id,
                workflow_id=workflow_id,
                tool=name,
                args=dict(args),
                requires_approval=requires_approval,
            )
            await self._store.set(key, result, meta)
        return result
