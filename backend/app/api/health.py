from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import Settings, get_settings
from app.core.readiness import check_readiness
from app.schemas.health import HealthResponse, LiveResponse, ReadinessResponse

SERVICE_NAME = "clouddesk-api"

router = APIRouter(tags=["health"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
async def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=__version__,
        environment=settings.environment,
    )


@router.get("/health/live")
async def live() -> LiveResponse:
    # Liveness probes must stay cheap and dependency-free, or a slow database restarts the pod.
    return LiveResponse(status="alive")


@router.get(
    "/health/ready", response_model=ReadinessResponse, responses={503: {"model": ReadinessResponse}}
)
async def ready(settings: SettingsDep) -> JSONResponse:
    checks = check_readiness(settings)
    degraded = any(check.status == "error" for check in checks.values())
    body = ReadinessResponse(status="degraded" if degraded else "ready", checks=checks)
    return JSONResponse(
        status_code=503 if degraded else 200, content=body.model_dump(exclude_none=True)
    )
