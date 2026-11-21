"""Audit log response types (docs/design/06_API_CONTRACT.md, Audit)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor: str
    actor_type: str
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any]
    request_id: str
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditLog]
    total: int
