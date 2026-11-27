"""Run the support workflow and keep its state (F11, F13, CLAUDE.md 4.1).

Does: `create_run` writes the `workflow_runs` row (the 202 the API returns), `start_workflow` runs
the graph in the background and saves the state after every node (the console polls it), and
`resume_workflow` continues a run that paused for approval. When the graph pauses, this service
writes the `approval_requests` and moves the ticket to `waiting_on_approval`; when it ends it
records the outcome on the run and the ticket. Failures are caught: a run that breaks ends as
`failed` with its error recorded, never as a hung process.
Must NOT: talk HTTP, hold agent or policy logic (the graph and the rules do), or execute an action
that needs approval before a person approved it.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from agents.checkpointer import is_memory, open_checkpointer
from agents.graph import build_graph
from agents.nodes.common import GraphDeps
from agents.nodes.decision import pending_approval_actions
from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.observability import WorkflowTracer
from app.repositories.approvals import ApprovalRepository
from app.repositories.customers import CustomerRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.repositories.workflow import WorkflowRunRepository
from app.schemas.common import (
    ApprovalStatus,
    MessageRole,
    Severity,
    TicketStatus,
    WorkflowEventType,
    WorkflowStatus,
)
from app.services.ticket_service import TicketNotFound
from app.tools.context import build_context
from app.tools.factory import build_default_registry

logger = logging.getLogger(__name__)

AI_AUTHOR = "CloudDesk AI"
APPROVAL_TTL = timedelta(hours=24)
# A run still marked running after this long is treated as dead (a restart drops in-flight runs).
RUN_STALE_AFTER = timedelta(minutes=15)

_memory_saver: InMemorySaver | None = None


class RunConflict(Exception):
    """The ticket is waiting on an approval, or the run is not in a state that allows this."""


class RunNotFound(Exception):
    pass


def reset_checkpointer() -> None:
    """Forget the in-memory checkpoints (tests start every case from nothing)."""
    global _memory_saver
    _memory_saver = None


@asynccontextmanager
async def _saver() -> AsyncIterator[BaseCheckpointSaver]:
    global _memory_saver
    path = get_settings().checkpoint_db_path
    if is_memory(path):
        if _memory_saver is None:
            _memory_saver = InMemorySaver()
        yield _memory_saver
        return
    async with open_checkpointer(path) as saver:
        yield saver


def _json_safe(values: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(values, default=str))


def _deps() -> GraphDeps:
    ctx = build_context()
    return GraphDeps(ctx=ctx, registry=build_default_registry(ctx))


async def create_run(session: AsyncSession, ticket_id: str) -> str:
    """Write the run row and return its id. 409 while an approval is pending or a run is live."""
    tickets = TicketRepository(session)
    ticket = await tickets.get(ticket_id)
    if ticket is None:
        raise TicketNotFound
    if ticket.status == TicketStatus.waiting_on_approval:
        raise RunConflict("The ticket is waiting on an approval.")
    runs = WorkflowRunRepository(session)
    latest = await runs.latest_for_ticket(ticket.id)
    if latest is not None and latest.status == WorkflowStatus.running:
        started = latest.started_at
        if started is not None and started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        if started is None or datetime.now(UTC) - started < RUN_STALE_AFTER:
            raise RunConflict("A run is already in progress for this ticket.")
    run_id = str(uuid.uuid4())
    await runs.create(
        id=run_id,
        ticket_id=ticket.id,
        thread_id=run_id,
        status=WorkflowStatus.running,
        state={},
        started_at=datetime.now(UTC),
    )
    if ticket.status == TicketStatus.new:
        await tickets.update(ticket.id, status=TicketStatus.in_progress)
    await session.commit()
    return run_id


async def start_workflow(run_id: str) -> None:
    """The background task: build the first state from the ticket and drive the graph."""
    try:
        async with get_sessionmaker()() as session:
            run = await WorkflowRunRepository(session).get(run_id)
            if run is None:
                return
            ticket = await TicketRepository(session).get(run.ticket_id)
            customer = await CustomerRepository(session).get(ticket.customer_id) if ticket else None
            if ticket is None or customer is None:
                await _fail(run_id, LookupError("ticket or customer missing"))
                return
            initial: dict[str, Any] = {
                "workflow_id": run.id,
                "ticket_id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "customer_id": customer.id,
                "subject": ticket.subject,
                "body": ticket.body,
                "plan_name": customer.plan_name,
                "step_count": 0,
            }
        await _drive(run_id, initial)
    except Exception as exc:  # noqa: BLE001 - a background task must not die silently
        logger.exception("workflow start failed")
        await _fail(run_id, exc)


async def resume_workflow(run_id: str, decision: str, note: str | None = None) -> None:
    """Continue a paused run with the person's decision."""
    try:
        await _drive(run_id, Command(resume={"decision": decision, "note": note}))
    except Exception as exc:  # noqa: BLE001
        logger.exception("workflow resume failed")
        await _fail(run_id, exc)


async def _drive(run_id: str, graph_input: Any) -> None:
    started = time.perf_counter()
    async with get_sessionmaker()() as session:
        run = await WorkflowRunRepository(session).get(run_id)
        if run is None:
            raise RunNotFound(run_id)
        thread_id = run.thread_id
    config = {"configurable": {"thread_id": thread_id}}
    async with _saver() as saver:
        graph = build_graph(_deps(), saver)
        async for values in graph.astream(graph_input, config, stream_mode="values"):
            await _save_state(run_id, values)
        snapshot = await graph.aget_state(config)
    values = snapshot.values
    paused = bool(snapshot.next) and any(task.interrupts for task in snapshot.tasks)
    if paused:
        await _handle_interrupt(run_id, values)
    else:
        await _complete(run_id, values, int((time.perf_counter() - started) * 1000))


async def _save_state(run_id: str, values: dict[str, Any]) -> None:
    async with get_sessionmaker()() as session:
        await WorkflowRunRepository(session).update(
            run_id,
            state=_json_safe(values),
            current_node=values.get("current_node"),
            token_usage=_json_safe(values.get("token_usage", {})),
            status=WorkflowStatus.running,
        )
        await session.commit()


async def _handle_interrupt(run_id: str, values: dict[str, Any]) -> None:
    """The graph paused for a person: record the approval requests and move the ticket."""
    async with get_sessionmaker()() as session:
        approvals = ApprovalRepository(session)
        first_id: str | None = None
        for action in pending_approval_actions(values.get("resolution_plan")):
            row = await approvals.create(
                ticket_id=values["ticket_id"],
                workflow_id=run_id,
                action=action,
                risk_level=(values.get("risk") or {}).get("level", "high"),
                reason="; ".join((values.get("risk") or {}).get("reasons", [])),
                requested_by="ai",
                status=ApprovalStatus.pending,
                expires_at=datetime.now(UTC) + APPROVAL_TTL,
            )
            first_id = first_id or row.id
        state = {**values, "approval_status": "pending", "approval_request_id": first_id}
        await WorkflowRunRepository(session).update(
            run_id,
            state=_json_safe(state),
            status=WorkflowStatus.waiting_for_approval,
            current_node="human_approval",
        )
        await TicketRepository(session).update(
            values["ticket_id"],
            status=TicketStatus.waiting_on_approval,
            approval_status=ApprovalStatus.pending,
            category=(values.get("classification") or {}).get("category"),
            severity=Severity(values["severity"]) if values.get("severity") else None,
        )
        await session.commit()
    await WorkflowTracer(get_sessionmaker(), run_id, values["ticket_id"]).event(
        WorkflowEventType.approval_requested,
        node="human_approval",
        message="A person must approve the proposed actions.",
        payload={"approval_request_id": first_id},
    )


async def _complete(run_id: str, values: dict[str, Any], duration_ms: int) -> None:
    escalated = bool(values.get("escalation_required"))
    status = WorkflowStatus.escalated if escalated else WorkflowStatus.completed
    async with get_sessionmaker()() as session:
        run = await WorkflowRunRepository(session).get(run_id)
        started = run.started_at if run else None
        total_ms = duration_ms
        if started is not None:
            started_utc = started if started.tzinfo else started.replace(tzinfo=UTC)
            total_ms = int((datetime.now(UTC) - started_utc).total_seconds() * 1000)
        await WorkflowRunRepository(session).update(
            run_id,
            state=_json_safe(values),
            status=status,
            current_node=values.get("current_node"),
            token_usage=_json_safe(values.get("token_usage", {})),
            finished_at=datetime.now(UTC),
            duration_ms=total_ms,
        )
        approval = values.get("approval_status")
        tickets = TicketRepository(session)
        current = await tickets.get(values["ticket_id"])
        if escalated:
            new_status = TicketStatus.escalated
        elif current is not None and current.status == TicketStatus.resolved:
            new_status = TicketStatus.resolved  # an `update_ticket` action already resolved it
        else:
            new_status = TicketStatus.in_progress
        await tickets.update(
            values["ticket_id"],
            status=new_status,
            escalation_required=escalated,
            approval_status=ApprovalStatus(approval) if approval else ApprovalStatus.not_required,
            category=(values.get("classification") or {}).get("category"),
            severity=Severity(values["severity"]) if values.get("severity") else None,
        )
        if values.get("final_response") and not escalated:
            await TicketMessageRepository(session).add(
                ticket_id=values["ticket_id"],
                role=MessageRole.ai,
                author_name=AI_AUTHOR,
                body=values["final_response"],
                internal=True,
            )
        await session.commit()
    await WorkflowTracer(get_sessionmaker(), run_id, values["ticket_id"]).event(
        WorkflowEventType.workflow_completed,
        message=f"workflow {status.value}",
        duration_ms=total_ms,
        payload={"status": status.value, "tokens": values.get("token_usage", {})},
    )


async def _fail(run_id: str, exc: Exception) -> None:
    """A run that broke ends as `failed`, with the error recorded."""
    ticket_id = ""
    try:
        async with get_sessionmaker()() as session:
            run = await WorkflowRunRepository(session).get(run_id)
            if run is None:
                return
            ticket_id = run.ticket_id
            state = dict(run.state or {})
            state["errors"] = [*state.get("errors", []), f"{type(exc).__name__}: {exc}"[:300]]
            await WorkflowRunRepository(session).update(
                run_id,
                state=_json_safe(state),
                status=WorkflowStatus.failed,
                finished_at=datetime.now(UTC),
            )
            await session.commit()
        await WorkflowTracer(get_sessionmaker(), run_id, ticket_id).event(
            WorkflowEventType.error,
            message=f"workflow failed: {type(exc).__name__}",
            payload={"error_type": type(exc).__name__},
        )
    except Exception:  # noqa: BLE001
        logger.exception("could not record a failed run")
