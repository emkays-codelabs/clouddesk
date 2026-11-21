"""Settings route (docs/design/06_API_CONTRACT.md, Settings). Read-only and redacted."""

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.settings import SettingsView
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=SettingsView)
async def read_settings() -> SettingsView:
    return settings_service.get_settings_view()
