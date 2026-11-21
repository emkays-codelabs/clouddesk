import logging

import jwt
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.logging import current_request_id
from app.core.security import decode_token
from app.repositories.audit import AuditLogRepository

logger = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
API_PREFIX = ("api", "v1")


def _actor(scope: Scope) -> tuple[str, str]:
    """Identity from a valid bearer token; anything else is anonymous. Never raises."""
    for name, value in scope["headers"]:
        if name == b"authorization":
            scheme, _, token = value.decode("latin-1").partition(" ")
            if scheme.lower() == "bearer" and token:
                try:
                    principal = decode_token(token.strip(), get_settings())
                except jwt.InvalidTokenError:
                    break
                return principal.email or principal.sub, "user"
            break
    return "anonymous", "anonymous"


def _resource(path: str) -> tuple[str, str]:
    """`/api/v1/tickets/42/reply` -> ("tickets", "42"); shorter paths leave the id empty."""
    parts = [p for p in path.split("/") if p]
    if tuple(parts[:2]) == API_PREFIX:
        parts = parts[2:]
    return (parts[0] if parts else ""), (parts[1] if len(parts) > 1 else "")


class AuditMiddleware:
    """Writes one audit_logs row for every state-changing request (N6).

    Plain ASGI. It records who (from the token), what (method and path), which resource, the status
    code and the request id; it never reads the body, the query string or any header besides
    Authorization, so no secret can reach the log. The write goes through AuditLogRepository, which
    owns the tenant filter. A failed write is logged and swallowed: auditing must not turn a
    successful request into an error.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        status_code = 500  # what the outer RequestId handler returns if the app raises

        async def send_and_capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_and_capture)
        finally:
            await self._record(scope, status_code)

    async def _record(self, scope: Scope, status_code: int) -> None:
        try:
            actor, actor_type = _actor(scope)
            resource_type, resource_id = _resource(scope["path"])
            async with get_sessionmaker()() as session:
                await AuditLogRepository(session).append(
                    actor=actor,
                    actor_type=actor_type,
                    action=f"{scope['method']} {scope['path']}"[:200],
                    resource_type=resource_type[:64],
                    resource_id=resource_id[:64],
                    details={"status_code": status_code},
                    request_id=(current_request_id() or "")[:64],
                )
                await session.commit()
        except Exception as exc:
            logger.error("audit write failed", extra={"error_type": type(exc).__name__})
