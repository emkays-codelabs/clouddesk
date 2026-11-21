import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.health import router as health_router
from app.api.tickets import router as tickets_router
from app.core.config import get_settings, redact_url
from app.core.database import create_tables, dispose_engine
from app.core.logging import setup_logging
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import HEADER as REQUEST_ID_HEADER
from app.middleware.request_id import RequestIdMiddleware
from app.services.seed_service import bootstrap_demo_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        await create_tables()
        await bootstrap_demo_data()
    except Exception as exc:
        # Log the class and a redacted URL only: SQLAlchemy messages can echo the URL, and a bad
        # database must still let /health/ready report `degraded` instead of failing startup.
        logger.error(
            "database startup failed",
            extra={
                "error_type": type(exc).__name__,
                "database_url": redact_url(get_settings().database_url),
            },
        )
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    app = FastAPI(title="CloudDesk AI API", version=__version__, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tickets_router, prefix="/api/v1")
    app.include_router(customers_router, prefix="/api/v1")

    # add_middleware wraps outward, so the last one added is outermost. Target order, outermost
    # first, is CORS -> RequestId -> RateLimit -> Audit (N6). A 429 therefore still carries the
    # request id and CORS headers, and the audit row sees the id RequestId already bound.
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware, limit=settings.rate_limit_per_minute)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    return app


app = create_app()
