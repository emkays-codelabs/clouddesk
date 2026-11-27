"""The human approval node (F9, CLAUDE.md 7.3): pause until a person decides.

Does: call `interrupt()` with the actions that need approval. The graph stops and the checkpointer
keeps its state under the run's `thread_id`. The service, not this node, writes the
`approval_requests` rows once it sees the pause (so the code that re-runs on resume stays tiny and
has no side effects). On resume the node receives the decision and stores `approval_status`.
Must NOT: do anything with a side effect before `interrupt()`, and must NOT approve by default.
"""

from typing import Any

from langgraph.types import interrupt

from agents.nodes.common import GraphDeps, NodeFn, progress
from agents.nodes.decision import pending_approval_actions
from agents.state import SupportState

APPROVAL = "human_approval"
APPROVED = "approved"
REJECTED = "rejected"


def human_approval(deps: GraphDeps) -> NodeFn:
    async def run(state: SupportState) -> dict[str, Any]:
        decision = interrupt(
            {
                "kind": "approval",
                "actions": pending_approval_actions(state.get("resolution_plan")),
                "reason": "; ".join((state.get("risk") or {}).get("reasons", [])),
            }
        )
        verdict = decision.get("decision") if isinstance(decision, dict) else decision
        status = APPROVED if verdict == APPROVED else REJECTED  # anything but approved is a refusal
        update: dict[str, Any] = {**progress(APPROVAL), "approval_status": status}
        if status == REJECTED:
            update["escalation_required"] = True
            update["escalation_reason"] = "A person rejected the proposed actions."
        return update

    run.__name__ = APPROVAL
    return run
