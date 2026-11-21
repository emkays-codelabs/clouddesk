"""JWT validation and role checks (N1, CLAUDE.md 2 and 9).

Tokens are HS256, signed with `settings.effective_jwt_secret` (the Supabase secret when set).
`require_role` is the only RBAC gate: routes declare the lowest role they accept.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

ALGORITHM = "HS256"
ROLE_RANK: dict[str, int] = {"viewer": 1, "agent": 2, "admin": 3}
DEFAULT_TTL_SECONDS = 8 * 3600  # demo tokens live 8 hours (CLAUDE.md 9)

# auto_error=False so a missing header is our 401 with WWW-Authenticate, not FastAPI's 403.
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    sub: str
    role: str
    email: str | None = None


def create_access_token(
    sub: str,
    role: str,
    *,
    email: str | None = None,
    expires_in_seconds: int = DEFAULT_TTL_SECONDS,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    now = int(time.time())
    claims: dict[str, Any] = {"sub": sub, "role": role, "iat": now, "exp": now + expires_in_seconds}
    if email:
        claims["email"] = email
    return jwt.encode(claims, settings.effective_jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, settings: Settings) -> Principal:
    """Verify signature and expiry; raise `jwt.InvalidTokenError` for anything unacceptable."""
    claims = jwt.decode(
        token,
        settings.effective_jwt_secret,
        algorithms=[ALGORITHM],  # pinned, so an `alg: none` or RS/HS confusion token is refused
        options={"require": ["exp", "sub"], "verify_aud": False},
    )
    role = claims.get("role")
    if role not in ROLE_RANK:
        raise jwt.InvalidTokenError("unknown role")
    return Principal(sub=str(claims["sub"]), role=role, email=claims.get("email"))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        return decode_token(credentials.credentials, settings)
    except jwt.InvalidTokenError:
        # One message for every failure: do not tell a caller why a token was refused.
        raise _unauthorized("Invalid or expired token") from None


def require_role(minimum: str) -> Callable[..., Principal]:
    """Dependency factory: accept `minimum` or any higher role, else 403."""
    if minimum not in ROLE_RANK:
        raise ValueError(f"unknown role {minimum!r}")

    async def dependency(user: Annotated[Principal, Depends(get_current_user)]) -> Principal:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency
