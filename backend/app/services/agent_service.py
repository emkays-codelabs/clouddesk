"""The agents overview (F13): the six agents, the graph, recent runs and run statistics.

Does: describe each specialist, count its runs from the nodes recorded in saved run states, and
sum run statistics (runs, failures, mean duration, tokens, estimated cost).
Must NOT: talk HTTP or run anything.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from agents.graph import GRAPH_EDGES, GRAPH_NODES
from app.repositories.workflow import WorkflowRunRepository
from app.schemas.approval import (
    AgentGraph,
    AgentInfo,
    AgentsOverview,
    AgentStats,
    GraphEdge,
    GraphNode,
)
from app.schemas.common import WorkflowStatus
from app.schemas.workflow import combine_basis
from app.services.ticket_service import _to_workflow

RECENT_RUNS = 10

# name, role, description, tools, graph nodes the agent owns
_AGENTS: list[tuple[str, str, str, list[str], set[str]]] = [
    (
        "Support Supervisor",
        "Understand",
        "Classifies the ticket, scores severity (rules may only raise it) and writes the summary.",
        [],
        {"understand_ticket", "classify_severity", "ticket_summary"},
    ),
    (
        "Customer Agent",
        "Investigate",
        "Loads the customer, subscription, workspace, earlier tickets and memory notes.",
        ["get_customer", "get_subscription", "get_ticket_history"],
        {"customer_context"},
    ),
    (
        "Knowledge Agent",
        "Retrieve",
        "Finds cited knowledge articles and similar resolved cases.",
        ["search_docs"],
        {"knowledge_retrieval"},
    ),
    (
        "Troubleshooting Agent",
        "Troubleshoot",
        "Proposes probable causes and numbered steps, checking service status.",
        ["check_service_status"],
        {"troubleshooting"},
    ),
    (
        "Resolution Agent",
        "Decide and act",
        "Drafts the reply and the action plan; actions come from the deterministic planner.",
        ["update_ticket", "create_refund_request", "reset_demo_setting"],
        {"resolution_planning", "execute_resolution", "memory_update"},
    ),
    (
        "Escalation Agent",
        "Escalate",
        "Hands policy cases to a named team; policy rules always win over the model.",
        ["create_escalation"],
        {"risk_check", "human_approval", "escalation"},
    ),
]


async def overview(session: AsyncSession) -> AgentsOverview:
    runs = await WorkflowRunRepository(session).list_recent(200)
    completed = [
        r for r in runs if r.status in (WorkflowStatus.completed, WorkflowStatus.escalated)
    ]
    failed = [r for r in runs if r.status == WorkflowStatus.failed]
    durations = [r.duration_ms for r in runs if r.duration_ms]
    tokens = sum(int((r.token_usage or {}).get("total_tokens", 0)) for r in runs)
    cost = sum(float((r.token_usage or {}).get("estimated_cost_usd", 0.0)) for r in runs)
    basis = "none"
    for r in runs:
        basis = combine_basis(basis, (r.token_usage or {}).get("cost_basis", "none"))

    agents: list[AgentInfo] = []
    for name, role, description, tools, nodes in _AGENTS:
        mine = [r for r in runs if nodes & set((r.state or {}).get("completed_nodes", []))]
        spans = [r.duration_ms for r in mine if r.duration_ms]
        agents.append(
            AgentInfo(
                name=name,
                role=role,
                description=description,
                tools=tools,
                last_run_at=max((r.started_at for r in mine if r.started_at), default=None),
                runs=len(mine),
                avg_duration_ms=round(sum(spans) / len(spans), 1) if spans else 0.0,
            )
        )
    return AgentsOverview(
        agents=agents,
        graph=AgentGraph(
            nodes=[GraphNode(**n) for n in GRAPH_NODES],
            edges=[GraphEdge(**e) for e in GRAPH_EDGES],
        ),
        recent_runs=[_to_workflow(r) for r in runs[:RECENT_RUNS]],
        stats=AgentStats(
            runs_total=len(runs),
            runs_completed=len(completed),
            runs_failed=len(failed),
            avg_duration_ms=round(sum(durations) / len(durations), 1) if durations else 0.0,
            total_tokens=tokens,
            total_estimated_cost_usd=round(cost, 6),
            cost_basis=basis,
        ),
    )
