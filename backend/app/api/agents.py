"""Agents overview route (docs/design/06_API_CONTRACT.md, Agents): the agents and their runs.

HTTP only. The graph shown is `GRAPH_NODES` and `GRAPH_EDGES`, so it cannot differ from the code.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.schemas.approval import AgentsOverview
from app.services import agent_service

router = APIRouter(tags=["agents"], dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/agents", response_model=AgentsOverview)
async def get_agents(session: Session) -> AgentsOverview:
    return await agent_service.overview(session)
