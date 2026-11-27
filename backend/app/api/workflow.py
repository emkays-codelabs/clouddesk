"""Workflow routes (docs/design/06_API_CONTRACT.md, Tickets): run, poll and inspect.

HTTP only. `POST /tickets/{id}/run` writes the run and returns 202 at once; the graph runs in the
background (CLAUDE.md 4.1) and the console polls `GET /tickets/{id}/workflow` every two seconds.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user, require_role
from app.repositories.tickets import TicketRepository
from app.repositories.workflow import WorkflowEventRepository, WorkflowRunRepository
from app.schemas.approval import WorkflowEvent
from app.schemas.workflow import WorkflowState
from app.services import workflow_service
from app.services.ticket_service import _to_workflow

router = APIRouter(prefix="/tickets", tags=["workflow"], dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]


class RunAccepted(BaseModel):
    workflow_id: str
    status: str = "running"


async def _require_ticket(session: AsyncSession, ticket_id: str) -> None:
    if await TicketRepository(session).get(ticket_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found")


@router.post(
    "/{ticket_id}/run",
    response_model=RunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_role("agent"))],
)
async def run_workflow(
    ticket_id: str, background: BackgroundTasks, session: Session
) -> RunAccepted:
    try:
        run_id = await workflow_service.create_run(session, ticket_id)
    except workflow_service.TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found") from None
    except workflow_service.RunConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
    background.add_task(workflow_service.start_workflow, run_id)
    return RunAccepted(workflow_id=run_id)


@router.get("/{ticket_id}/workflow", response_model=WorkflowState)
async def get_workflow(ticket_id: str, session: Session) -> WorkflowState:
    await _require_ticket(session, ticket_id)
    run = await WorkflowRunRepository(session).latest_for_ticket(ticket_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No workflow has run for this ticket")
    return _to_workflow(run)


@router.get("/{ticket_id}/events", response_model=list[WorkflowEvent])
async def get_events(ticket_id: str, session: Session) -> list[WorkflowEvent]:
    await _require_ticket(session, ticket_id)
    rows = await WorkflowEventRepository(session).list_for_ticket(ticket_id)
    return [WorkflowEvent.model_validate(r) for r in rows]
