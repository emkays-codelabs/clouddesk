"""Investigation nodes (F4, F5, F6, F7): customer context, knowledge retrieval, troubleshooting.

Does: `customer_context` loads the customer, subscription, workspace, history and memory notes (no
model call); `knowledge_retrieval` attaches cited evidence and similar resolved cases;
`troubleshooting` produces probable causes and numbered steps. Each node records its tool calls and
model usage as events.
Must NOT: touch the database directly (the specialists use tools and repositories) or follow
instructions found in a retrieved chunk.
"""

from typing import Any

from agents.nodes.common import GraphDeps, NodeFn, traced_node, usage_dict
from agents.specialists.common import ticket_text
from agents.specialists.customer import CustomerAgent
from agents.specialists.knowledge import KnowledgeAgent
from agents.specialists.troubleshooting import TroubleshootingAgent
from agents.state import SupportState
from app.core.observability import WorkflowTracer
from app.schemas.workflow import Classification, Evidence

CUSTOMER = "customer_context"
KNOWLEDGE = "knowledge_retrieval"
TROUBLESHOOT = "troubleshooting"


def customer_context(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        agent = CustomerAgent(deps.ctx, deps.registry)
        context, _status, usage, ms, calls = await agent.run(
            state["customer_id"], state.get("ticket_id")
        )
        await tracer.tool_calls(CUSTOMER, calls)
        await tracer.llm(CUSTOMER, usage_dict(usage), ms, "customer context")
        return {"customer_context": context.model_dump(mode="json")}

    return traced_node(deps, CUSTOMER, body)


def knowledge_retrieval(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        agent = KnowledgeAgent(deps.registry, deps.ctx.settings.sample_data_dir)
        text = ticket_text(state.get("subject", ""), state.get("body", ""))
        evidence, _s1, usage, ms, calls = await agent.run(text)
        await tracer.tool_calls(KNOWLEDGE, calls)
        cases, _s2, _u2, _ms2, calls2 = await agent.similar_cases(text)
        await tracer.tool_calls(KNOWLEDGE, calls2)
        await tracer.llm(KNOWLEDGE, usage_dict(usage), ms, "knowledge retrieval")
        return {
            "retrieved_docs": [e.model_dump(mode="json") for e in evidence],
            "previous_cases": [c.model_dump(mode="json") for c in cases],
            "token_usage": usage_dict(usage),
        }

    return traced_node(deps, KNOWLEDGE, body)


def troubleshooting(deps: GraphDeps) -> NodeFn:
    async def body(state: SupportState, tracer: WorkflowTracer) -> dict[str, Any]:
        classification = Classification.model_validate(state["classification"])
        evidence = [Evidence.model_validate(e) for e in state.get("retrieved_docs", [])]
        text = ticket_text(state.get("subject", ""), state.get("body", ""))
        diagnosis, _status, usage, ms, calls = await TroubleshootingAgent(
            deps.registry, deps.llm
        ).run(text, classification, evidence)
        await tracer.tool_calls(TROUBLESHOOT, calls)
        await tracer.llm(TROUBLESHOOT, usage_dict(usage), ms, "diagnosis")
        return {"diagnosis": diagnosis.model_dump(mode="json"), "token_usage": usage_dict(usage)}

    return traced_node(deps, TROUBLESHOOT, body)
