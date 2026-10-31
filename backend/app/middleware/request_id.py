import logging
import re
import uuid

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import log_context

HEADER = "X-Request-ID"
# fullmatch, not match: "$" would let a trailing newline through.
_SAFE_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")

logger = logging.getLogger(__name__)


def _resolve_request_id(scope: Scope) -> str:
    """Echo a caller's id only when it is safe to log and reflect; otherwise issue a UUID."""
    for name, value in scope["headers"]:
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            if _SAFE_ID.fullmatch(candidate):
                return candidate
            break
    return str(uuid.uuid4())


class RequestIdMiddleware:
    """Gives every HTTP response an X-Request-ID and binds it to the log context.

    Written as plain ASGI (not BaseHTTPMiddleware) so the id also reaches responses for unhandled
    errors: Starlette's own 500 handler sits outside user middleware and would skip the header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _resolve_request_id(scope)
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)[HEADER] = request_id
            await send(message)

        with log_context(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_id)
            except Exception:
                logger.exception("unhandled error")
                if response_started:
                    raise
                response = JSONResponse(
                    {"detail": "Internal Server Error"},
                    status_code=500,
                    headers={HEADER: request_id},
                )
                await response(scope, receive, send)
