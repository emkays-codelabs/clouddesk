"""Tool introspection route (docs/design/06_API_CONTRACT.md, MCP). HTTP only."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.mcp import ToolsResponse
from app.services import tool_service

router = APIRouter(prefix="/mcp", tags=["mcp"], dependencies=[Depends(get_current_user)])


@router.get("/tools", response_model=ToolsResponse)
async def list_tools() -> ToolsResponse:
    return tool_service.list_tools()
