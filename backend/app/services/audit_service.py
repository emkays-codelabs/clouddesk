"""Audit log reads (N6). Writing is done by the audit middleware."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit import AuditLogRepository
from app.schemas.audit import AuditLog, AuditPage


async def list_audit(
    session: AsyncSession, *, page: int, page_size: int, actor: str | None, action: str | None
) -> AuditPage:
    rows, total = await AuditLogRepository(session).list(
        page=page, page_size=page_size, actor=actor, action=action
    )
    return AuditPage(items=[AuditLog.model_validate(r) for r in rows], total=total)
