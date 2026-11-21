"""Audit log route (docs/design/06_API_CONTRACT.md, Audit). HTTP only."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.repositories.base import MAX_PAGE_SIZE
from app.schemas.audit import AuditPage
from app.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=AuditPage)
async def list_audit(
    session: Annotated[AsyncSession, Depends(get_session)],
    actor: str | None = None,
    action: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
) -> AuditPage:
    return await audit_service.list_audit(
        session, page=page, page_size=page_size, actor=actor, action=action
    )
