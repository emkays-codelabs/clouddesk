"""The support workflow graph (CLAUDE.md 7.3): twelve steps, three routes after the risk check.

```text
understand_ticket -> classify_severity -> customer_context -> knowledge_retrieval -> troubleshooting
  -> resolution_planning -> risk_check
      |- escalation_required      -> escalation
      |- approval pending         -> human_approval (interrupt) -approved-> execute_resolution
      |                                                        `-rejected-> escalation
      `- low risk                 -> execute_resolution
  -> ticket_summary -> memory_update -> END
```

Does: build the graph from a `GraphDeps` and a checkpointer. `GRAPH_NODES` and `GRAPH_EDGES` are
what `GET /api/v1/agents` and the console render, so the picture can never differ from the
graph. A node that fails sets `failed`, and every edge after it goes to `escalation`, so a broken
step ends the run in a human's hands instead of looping or crashing. The run budgets (12 steps,
confidence 0.6) are enforced in `risk_check`.
Must NOT: hold node logic (it is in `agents/nodes/`), or know about HTTP.
"""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agents.nodes import decision, escalation, human_approval, investigate, supervisor
from agents.nodes.common import GraphDeps
from agents.nodes.decision import pending_approval_actions
from agents.state import SupportState

UNDERSTAND = supervisor.UNDERSTAND
CLASSIFY = supervisor.CLASSIFY
CUSTOMER = investigate.CUSTOMER
KNOWLEDGE = investigate.KNOWLEDGE
TROUBLESHOOT = investigate.TROUBLESHOOT
PLANNING = decision.PLANNING
RISK = decision.RISK
APPROVAL = human_approval.APPROVAL
EXECUTE = decision.EXECUTE
ESCALATION = escalation.ESCALATION
SUMMARY = supervisor.SUMMARY
MEMORY = decision.MEMORY

# The twelve steps the console renders, in order (label shown in the workflow panel).
GRAPH_NODES: list[dict[str, str]] = [
    {"id": UNDERSTAND, "label": "Understand ticket"},
    {"id": CLASSIFY, "label": "Classify severity"},
    {"id": CUSTOMER, "label": "Customer context"},
    {"id": KNOWLEDGE, "label": "Knowledge retrieval"},
    {"id": TROUBLESHOOT, "label": "Troubleshooting"},
    {"id": PLANNING, "label": "Resolution planning"},
    {"id": RISK, "label": "Risk check"},
    {"id": APPROVAL, "label": "Human approval"},
    {"id": EXECUTE, "label": "Execute resolution"},
    {"id": ESCALATION, "label": "Escalation"},
    {"id": SUMMARY, "label": "Ticket summary"},
    {"id": MEMORY, "label": "Memory update"},
]

GRAPH_EDGES: list[dict[str, str]] = [
    {"source": UNDERSTAND, "target": CLASSIFY},
    {"source": CLASSIFY, "target": CUSTOMER},
    {"source": CUSTOMER, "target": KNOWLEDGE},
    {"source": KNOWLEDGE, "target": TROUBLESHOOT},
    {"source": TROUBLESHOOT, "target": PLANNING},
    {"source": PLANNING, "target": RISK},
    {"source": RISK, "target": ESCALATION, "label": "policy, budget or low confidence"},
    {"source": RISK, "target": APPROVAL, "label": "needs approval"},
    {"source": RISK, "target": EXECUTE, "label": "low risk"},
    {"source": APPROVAL, "target": EXECUTE, "label": "approved"},
    {"source": APPROVAL, "target": ESCALATION, "label": "rejected"},
    {"source": EXECUTE, "target": SUMMARY},
    {"source": ESCALATION, "target": SUMMARY},
    {"source": SUMMARY, "target": MEMORY},
]


def _or_escalate(next_node: str):
    """After a node: escalate if it failed, otherwise carry on."""

    def route(state: SupportState) -> str:
        return ESCALATION if state.get("failed") else next_node

    return route


def route_after_risk(state: SupportState) -> str:
    if state.get("failed") or state.get("escalation_required"):
        return ESCALATION
    if pending_approval_actions(state.get("resolution_plan")):
        return APPROVAL
    return EXECUTE


def route_after_approval(state: SupportState) -> str:
    return EXECUTE if state.get("approval_status") == human_approval.APPROVED else ESCALATION


def build_graph(deps: GraphDeps, checkpointer: BaseCheckpointSaver | None) -> Any:
    graph = StateGraph(SupportState)
    graph.add_node(UNDERSTAND, supervisor.understand_ticket(deps))
    graph.add_node(CLASSIFY, supervisor.classify_severity(deps))
    graph.add_node(CUSTOMER, investigate.customer_context(deps))
    graph.add_node(KNOWLEDGE, investigate.knowledge_retrieval(deps))
    graph.add_node(TROUBLESHOOT, investigate.troubleshooting(deps))
    graph.add_node(PLANNING, decision.resolution_planning(deps))
    graph.add_node(RISK, decision.risk_check(deps))
    graph.add_node(APPROVAL, human_approval.human_approval(deps))
    graph.add_node(EXECUTE, decision.execute_resolution(deps))
    graph.add_node(ESCALATION, escalation.escalation(deps))
    graph.add_node(SUMMARY, supervisor.ticket_summary(deps))
    graph.add_node(MEMORY, decision.memory_update(deps))

    graph.add_edge(START, UNDERSTAND)
    chain = [UNDERSTAND, CLASSIFY, CUSTOMER, KNOWLEDGE, TROUBLESHOOT, PLANNING]
    for current, following in zip(chain, [*chain[1:], RISK], strict=True):
        graph.add_conditional_edges(
            current, _or_escalate(following), {following: following, ESCALATION: ESCALATION}
        )
    graph.add_conditional_edges(
        RISK, route_after_risk, {ESCALATION: ESCALATION, APPROVAL: APPROVAL, EXECUTE: EXECUTE}
    )
    graph.add_conditional_edges(
        APPROVAL, route_after_approval, {EXECUTE: EXECUTE, ESCALATION: ESCALATION}
    )
    graph.add_edge(EXECUTE, SUMMARY)
    graph.add_edge(ESCALATION, SUMMARY)
    graph.add_edge(SUMMARY, MEMORY)
    graph.add_edge(MEMORY, END)
    return graph.compile(checkpointer=checkpointer)
