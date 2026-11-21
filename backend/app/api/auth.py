"""Auth routes: demo login (DEMO_MODE only) and the current user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.security import Principal, get_current_user
from app.schemas.auth import DemoLoginRequest, TokenResponse, User
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(
    body: DemoLoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        return await auth_service.demo_login(session, body.email, body.role)
    except auth_service.DemoLoginRefused:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Unknown demo user") from None


@router.get("/me", response_model=User)
async def me(
    principal: Annotated[Principal, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user = await auth_service.get_user(session, principal.sub)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
