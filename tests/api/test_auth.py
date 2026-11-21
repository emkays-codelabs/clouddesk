"""P3-1 (N1): JWT validation and role ranking. A viewer must never pass a mutating route."""

import time
from typing import Annotated

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.security import ROLE_RANK, Principal, create_access_token, require_role

DEMO_SECRET = "change-me-demo-only"

# The demo secret is deliberately short; the warning is about production keys, not this fixture.
pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")


@pytest.fixture
def secured_client() -> TestClient:
    """A throwaway app with one route per role, so the guard is tested apart from real routes."""
    app = FastAPI()

    @app.get("/read")
    async def read(user: Annotated[Principal, Depends(require_role("viewer"))]):
        return {"sub": user.sub, "role": user.role}

    @app.post("/mutate")
    async def mutate(user: Annotated[Principal, Depends(require_role("agent"))]):
        return {"sub": user.sub}

    @app.post("/admin")
    async def admin(user: Annotated[Principal, Depends(require_role("admin"))]):
        return {"sub": user.sub}

    return TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestEffectiveSecret:
    def test_jwt_secret_is_used_when_no_supabase_secret(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
        monkeypatch.setenv("JWT_SECRET", "local-secret")
        assert Settings().effective_jwt_secret == "local-secret"

    def test_supabase_secret_is_preferred_when_set(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "supabase-secret")
        monkeypatch.setenv("JWT_SECRET", "local-secret")
        assert Settings().effective_jwt_secret == "supabase-secret"


class TestRoleRanking:
    def test_ranks_are_viewer_agent_admin(self):
        assert ROLE_RANK == {"viewer": 1, "agent": 2, "admin": 3}


class TestTokens:
    def test_missing_token_is_401(self, secured_client):
        response = secured_client.get("/read")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_garbage_token_is_401(self, secured_client):
        assert secured_client.get("/read", headers=_bearer("not-a-jwt")).status_code == 401

    def test_non_bearer_scheme_is_401(self, secured_client):
        headers = {"Authorization": "Basic abc"}
        assert secured_client.get("/read", headers=headers).status_code == 401

    def test_wrong_secret_is_401(self, secured_client):
        token = jwt.encode(
            {"sub": "u1", "role": "agent", "exp": int(time.time()) + 60}, "x" * 32, "HS256"
        )
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 401

    def test_expired_token_is_401(self, secured_client):
        token = create_access_token("u1", "agent", expires_in_seconds=-10)
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 401

    def test_token_without_expiry_is_401(self, secured_client):
        token = jwt.encode({"sub": "u1", "role": "agent"}, DEMO_SECRET, "HS256")
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 401

    def test_token_without_subject_is_401(self, secured_client):
        token = jwt.encode({"role": "agent", "exp": int(time.time()) + 60}, DEMO_SECRET, "HS256")
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 401

    def test_unknown_role_is_401(self, secured_client):
        token = create_access_token("u1", "superuser")
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 401

    def test_alg_none_token_is_401(self, secured_client):
        token = jwt.encode(
            {"sub": "u1", "role": "admin", "exp": int(time.time()) + 60}, None, "none"
        )
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 401

    def test_token_signed_with_supabase_secret_when_configured(self, secured_client, monkeypatch):
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "s" * 40)
        get_settings.cache_clear()
        good = create_access_token("u1", "agent")
        assert secured_client.post("/mutate", headers=_bearer(good)).status_code == 200
        old = jwt.encode(
            {"sub": "u1", "role": "agent", "exp": int(time.time()) + 60}, DEMO_SECRET, "HS256"
        )
        assert secured_client.post("/mutate", headers=_bearer(old)).status_code == 401


class TestRequireRole:
    def test_agent_token_is_accepted_on_mutating_route(self, secured_client):
        token = create_access_token("sam", "agent", email="sam.agent@clouddesk.demo")
        response = secured_client.post("/mutate", headers=_bearer(token))
        assert response.status_code == 200
        assert response.json() == {"sub": "sam"}

    def test_viewer_is_403_on_mutating_route(self, secured_client):
        token = create_access_token("vic", "viewer", email="vic.viewer@clouddesk.demo")
        assert secured_client.post("/mutate", headers=_bearer(token)).status_code == 403

    def test_viewer_can_read(self, secured_client):
        token = create_access_token("vic", "viewer")
        assert secured_client.get("/read", headers=_bearer(token)).status_code == 200

    def test_agent_is_403_on_admin_route(self, secured_client):
        token = create_access_token("sam", "agent")
        assert secured_client.post("/admin", headers=_bearer(token)).status_code == 403

    def test_admin_passes_every_route(self, secured_client):
        token = create_access_token("ada", "admin")
        for method, path in (("get", "/read"), ("post", "/mutate"), ("post", "/admin")):
            assert getattr(secured_client, method)(path, headers=_bearer(token)).status_code == 200

    def test_unknown_required_role_is_a_programming_error(self):
        with pytest.raises(ValueError):
            require_role("root")


class TestFixtures:
    def test_auth_fixtures_carry_each_role(self, agent_headers, admin_headers, viewer_headers):
        secret = get_settings().effective_jwt_secret
        roles = {}
        for name, headers in (
            ("agent", agent_headers),
            ("admin", admin_headers),
            ("viewer", viewer_headers),
        ):
            token = headers["Authorization"].removeprefix("Bearer ")
            roles[name] = jwt.decode(token, secret, algorithms=["HS256"])["role"]
        assert roles == {"agent": "agent", "admin": "admin", "viewer": "viewer"}
