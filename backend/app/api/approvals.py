"""Approval and escalation routes (docs/design/06_API_CONTRACT.md, Approvals and Escalations).

HTTP only. Approve and reject need the `agent` role (a viewer gets 403), and a decision on a run
that is not paused is 409.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import Principal, get_current_user, require_role
from app.schemas.approval import (
    ApprovalDecisionBody,
    ApprovalDecisionResult,
    ApprovalRequest,
    EscalationUpdate,
)
from app.schemas.common import ApprovalStatus, EscalationStatus
from app.schemas.workflow import Escalation
from app.services import approval_service, workflow_service

router = APIRouter(tags=["approvals"], dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]
Agent = Annotated[Principal, Depends(require_role("agent"))]


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


@router.get("/approvals", response_model=list[ApprovalRequest])
async def list_approvals(session: Session, status: ApprovalStatus | None = None):
    return await approval_service.list_approvals(session, status)


@router.get("/approvals/{approval_id}", response_model=ApprovalRequest)
async def get_approval(approval_id: str, session: Session):
    try:
        return await approval_service.get_approval(session, approval_id)
    except approval_service.ApprovalNotFound:
        raise _not_found("Approval") from None


async def _decide(
    approval_id: str,
    decision: ApprovalStatus,
    body: ApprovalDecisionBody,
    session: AsyncSession,
    user: Principal,
) -> ApprovalDecisionResult:
    try:
        return await approval_service.decide(session, approval_id, decision, body.note, user)
    except approval_service.ApprovalNotFound:
        raise _not_found("Approval") from None
    except workflow_service.RunConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalDecisionResult)
async def approve(approval_id: str, body: ApprovalDecisionBody, session: Session, user: Agent):
    return await _decide(approval_id, ApprovalStatus.approved, body, session, user)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalDecisionResult)
async def reject(approval_id: str, body: ApprovalDecisionBody, session: Session, user: Agent):
    return await _decide(approval_id, ApprovalStatus.rejected, body, session, user)


@router.get("/escalations", response_model=list[Escalation])
async def list_escalations(session: Session, status: EscalationStatus | None = None):
    return await approval_service.list_escalations(session, status)


@router.patch("/escalations/{escalation_id}", response_model=Escalation)
async def update_escalation(
    escalation_id: str, body: EscalationUpdate, session: Session, user: Agent
):
    try:
        return await approval_service.update_escalation(
            session, escalation_id, body.status, body.note, user
        )
    except approval_service.EscalationNotFound:
        raise _not_found("Escalation") from None
