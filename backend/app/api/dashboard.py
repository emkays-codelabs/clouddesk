"""Dashboard route (docs/design/06_API_CONTRACT.md, Dashboard). HTTP only."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)]
)


@router.get("/summary", response_model=DashboardSummary)
async def summary(session: Annotated[AsyncSession, Depends(get_session)]) -> DashboardSummary:
    return await dashboard_service.get_summary(session)
