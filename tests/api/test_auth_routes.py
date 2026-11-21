"""P3-2 (N1): demo login and /auth/me. Tokens last 8 hours and never carry a server secret."""

import jwt
import pytest

from app.core.config import get_settings

LOGIN = "/api/v1/auth/demo-login"
ME = "/api/v1/auth/me"
USERS = [
    ("admin@clouddesk.demo", "admin"),
    ("sam.agent@clouddesk.demo", "agent"),
    ("vic.viewer@clouddesk.demo", "viewer"),
]

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")


@pytest.mark.parametrize(("email", "role"), USERS)
def test_demo_login_issues_an_8_hour_token_for_each_demo_user(client, email, role):
    response = client.post(LOGIN, json={"email": email})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == email and body["user"]["role"] == role
    claims = jwt.decode(
        body["access_token"], get_settings().effective_jwt_secret, algorithms=["HS256"]
    )
    assert claims["role"] == role and claims["sub"] == body["user"]["id"]
    assert claims["exp"] - claims["iat"] == 8 * 3600


@pytest.mark.parametrize(("email", "role"), USERS)
def test_demo_login_by_role_alone_picks_that_roles_user(client, email, role):
    response = client.post(LOGIN, json={"role": role})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == email


def test_me_returns_the_user_behind_the_token(client):
    token = client.post(LOGIN, json={"email": "sam.agent@clouddesk.demo"}).json()["access_token"]

    response = client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "sam.agent@clouddesk.demo" and body["role"] == "agent"
    assert body["full_name"]


def test_me_without_a_token_is_401(client):
    assert client.get(ME).status_code == 401


def test_me_with_a_bad_token_is_401(client):
    assert client.get(ME, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_unknown_email_is_401(client):
    assert client.post(LOGIN, json={"email": "mallory@evil.example"}).status_code == 401


def test_email_and_role_that_disagree_are_401(client):
    response = client.post(LOGIN, json={"email": "vic.viewer@clouddesk.demo", "role": "admin"})
    assert response.status_code == 401


def test_an_empty_body_is_422(client):
    assert client.post(LOGIN, json={}).status_code == 422


def test_an_unknown_role_is_422(client):
    assert client.post(LOGIN, json={"role": "root"}).status_code == 422


def test_demo_login_is_404_when_demo_mode_is_off(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()

    response = client.post(LOGIN, json={"email": "admin@clouddesk.demo"})

    assert response.status_code == 404


def test_responses_never_contain_a_server_secret(client, monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "service-role-secret-xyz")
    monkeypatch.setenv("JWT_SECRET", "signing-secret-abc")
    get_settings.cache_clear()

    login = client.post(LOGIN, json={"role": "admin"})
    token = login.json()["access_token"]
    me = client.get(ME, headers={"Authorization": f"Bearer {token}"})

    for text in (login.text, me.text):
        assert "service-role-secret-xyz" not in text and "signing-secret-abc" not in text
    assert set(login.json()) == {"access_token", "token_type", "user"}
    assert set(login.json()["user"]) <= {"id", "email", "full_name", "role", "avatar_url"}
