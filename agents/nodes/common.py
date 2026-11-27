"""Shared node plumbing: the dependencies a node needs and the wrapper every node runs inside.

Does: `GraphDeps` carries the tool context, the registry and an optional model, so a node reaches
for nothing global. `traced_node` gives every node the same shape (CLAUDE.md 7.3): a `node_started`
and `node_completed` event with a duration, the shared progress fields (`completed_nodes`,
`route_history`, `step_count`, `current_node`), and a failure rule: an exception inside a node is
recorded, turned into `failed` plus an escalation reason, and the run moves to `escalation` instead
of crashing or looping.
Must NOT: hold agent logic (that is `agents/specialists/`), write SQL, or call a model.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from agents.state import SupportState
from app.core.llm import LLMProvider
from app.core.observability import WorkflowTracer
from app.tools.context import ToolContext
from app.tools.registry import ToolRegistry

NodeBody = Callable[[SupportState, WorkflowTracer], Awaitable[dict[str, Any]]]
NodeFn = Callable[[SupportState], Awaitable[dict[str, Any]]]


@dataclass
class GraphDeps:
    ctx: ToolContext
    registry: ToolRegistry
    llm: LLMProvider | None = None

    def tracer(self, state: SupportState) -> WorkflowTracer:
        return WorkflowTracer(
            self.ctx.session_factory, state.get("workflow_id", ""), state.get("ticket_id", "")
        )


def progress(name: str) -> dict[str, Any]:
    return {
        "completed_nodes": [name],
        "route_history": [name],
        "step_count": 1,
        "current_node": name,
    }


def traced_node(deps: GraphDeps, name: str, body: NodeBody) -> NodeFn:
    async def run(state: SupportState) -> dict[str, Any]:
        tracer = deps.tracer(state)
        try:
            async with tracer.node(name):
                update = await body(state, tracer)
        except Exception as exc:  # noqa: BLE001 - a node failure must not crash the graph
            return {
                **progress(name),
                "failed": True,
                "escalation_required": True,
                "escalation_reason": f"The {name} step failed ({type(exc).__name__}).",
                "errors": [f"{name}: {type(exc).__name__}: {exc}"[:300]],
            }
        return {**update, **progress(name)}

    run.__name__ = name
    return run


def usage_dict(usage: Any) -> dict[str, Any]:
    return usage.model_dump(mode="json")
