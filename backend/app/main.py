from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.middleware.request_id import HEADER as REQUEST_ID_HEADER
from app.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    app = FastAPI(title="CloudDesk API", version=__version__)
    app.include_router(health_router)

    # add_middleware wraps outward, so the last one added is outermost. Target order, outermost
    # first, is CORS -> RequestId -> RateLimit -> Audit; Phases 3 adds the last two below RequestId.
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
