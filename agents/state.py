"""The workflow state (F11, CLAUDE.md 7.3): what every graph node reads and returns.

Does: define `SupportState`, a `TypedDict` the LangGraph graph passes between nodes. Every node
returns a PARTIAL dict. Three fields use reducers so concurrent or repeated returns never overwrite
each other: `errors`, `completed_nodes` and `route_history` append, `step_count` adds, and
`token_usage` sums through `merge_usage`. Values are plain JSON-safe dicts (a Pydantic model is
turned into a dict with `model_dump(mode="json")`), so the checkpointer and `workflow_runs.state`
can store the state as it is.
Must NOT: hold behaviour, large documents in the reducer fields, or any database handle.
"""

import operator
from typing import Annotated, Any, TypedDict

# Budgets that end a run instead of letting it loop (CLAUDE.md 7.2, upstream FR-22).
MAX_GRAPH_STEPS = 12
ESCALATE_CONFIDENCE = 0.6

_USAGE_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens")


def merge_usage(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Sum two token-usage dicts. Missing keys count as zero; cost is rounded to 8 places."""
    left, right = left or {}, right or {}
    merged: dict[str, Any] = {k: int(left.get(k, 0)) + int(right.get(k, 0)) for k in _USAGE_KEYS}
    cost = float(left.get("estimated_cost_usd", 0.0)) + float(right.get("estimated_cost_usd", 0.0))
    merged["estimated_cost_usd"] = round(cost, 8)
    return merged


class SupportState(TypedDict, total=False):
    # Identity and the ticket as it was when the run started. No tenant field: the tenant filter
    # lives only in the repositories (CLAUDE.md 6).
    workflow_id: str
    ticket_id: str
    ticket_number: str
    customer_id: str
    subject: str
    body: str
    plan_name: str | None

    # What each node produced.
    classification: dict[str, Any]
    severity: str
    severity_reason: str
    severity_confidence: float
    injection_flags: list[str]
    customer_context: dict[str, Any]
    retrieved_docs: list[dict[str, Any]]
    previous_cases: list[dict[str, Any]]
    diagnosis: dict[str, Any]
    resolution_plan: dict[str, Any]
    risk: dict[str, Any]
    escalation_required: bool
    escalation_reason: str
    escalation: dict[str, Any]
    approval_status: str
    approval_request_id: str
    actions: list[dict[str, Any]]
    final_response: str
    ticket_summary: str
    memory_written: int

    # Progress. These are the only fields that accumulate.
    current_node: str
    errors: Annotated[list[str], operator.add]
    completed_nodes: Annotated[list[str], operator.add]
    route_history: Annotated[list[str], operator.add]
    step_count: Annotated[int, operator.add]
    token_usage: Annotated[dict[str, Any], merge_usage]
