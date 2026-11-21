import logging
import time
from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.redis import get_redis

WINDOW_SECONDS = 60
# Probes must keep answering when a client is throttled, or an orchestrator restarts a healthy pod.
EXEMPT_PREFIXES = ("/health",)

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Fixed-window limit per client (N2): at most `limit` requests per 60-second window.

    Plain ASGI, like RequestIdMiddleware. The client is the socket peer, never a header such as
    X-Forwarded-For, which a caller can forge to get a fresh budget. If Redis is unreachable the
    request is let through and an error is logged: an outage in the limiter must not take the API
    down with it.
    """

    def __init__(
        self,
        app: ASGIApp,
        limit: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.app = app
        self.limit = limit
        self.clock = clock

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        now = int(self.clock())
        window = now // WINDOW_SECONDS
        client = scope["client"][0] if scope.get("client") else "unknown"
        key = f"ratelimit:{client}:{window}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, WINDOW_SECONDS * 2)
        except Exception as exc:
            logger.error("rate limiter unavailable", extra={"error_type": type(exc).__name__})
            await self.app(scope, receive, send)
            return

        if count > self.limit:
            retry_after = (window + 1) * WINDOW_SECONDS - now
            response = JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
