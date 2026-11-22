"""Tool listing types (docs/design/06_API_CONTRACT.md, MCP)."""

from pydantic import BaseModel


class ToolInfo(BaseModel):
    name: str
    description: str
    requires_approval: bool


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]
