"""P4-5: GET /settings is redacted. It reports whether a key exists, never the key or any URL."""

import pytest

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

SETTINGS = "/api/v1/settings"
SECRETS = {
    "LLM_API_KEY": "sk-test-llm-SECRET-123",
    "QDRANT_API_KEY": "qdrant-SECRET-456",
    "LANGCHAIN_API_KEY": "lc-SECRET-789",
    "JWT_SECRET": "jwt-SECRET-000",
    "SUPABASE_JWT_SECRET": "supa-SECRET-111",
    "QDRANT_URL": "https://qdrant.internal.example:6333",
    "REDIS_URL": "redis://:redis-SECRET-222@cache.internal.example:6379/0",
    "DATABASE_URL": "postgresql+asyncpg://user:db-SECRET-333@db.internal.example/app",
}


def test_unauthenticated_gets_401(client):
    assert client.get(SETTINGS).status_code == 401


def test_defaults_match_the_contract(client, viewer_headers):
    response = client.get(SETTINGS, headers=viewer_headers)

    assert response.status_code == 200
    assert response.json() == {
        "demo_mode": True,
        "environment": "test",
        "llm": {
            "llm_provider": "fake",
            "llm_model": "",
            "embedding_provider": "fake",
            "embedding_model": "",
            "api_key_configured": False,
            "tracing": False,
        },
        "vector_store": "memory",
        "redis": "fake",
        "database": "sqlite",
        "approval_policy": {
            "refunds_require_approval": True,
            "max_refund_without_approval": 0,
            "approval_required_tools": ["create_refund_request", "reset_demo_setting"],
        },
    }


def test_a_configured_key_is_a_boolean_and_nothing_secret_is_returned(
    client, viewer_headers, monkeypatch
):
    # The app is already running on the test database; only the settings object changes.
    for name, value in SECRETS.items():
        if name != "DATABASE_URL":
            monkeypatch.setenv(name, value)
    monkeypatch.setenv("USE_FAKE_REDIS", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    from app.core import config

    real = config.Settings

    def with_postgres_url(**kwargs):
        return real(database_url=SECRETS["DATABASE_URL"], **kwargs)

    monkeypatch.setattr("app.services.settings_service.get_settings", lambda: with_postgres_url())

    response = client.get(SETTINGS, headers=viewer_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["llm"]["api_key_configured"] is True
    assert body["llm"]["tracing"] is True
    assert body["redis"] == "real"
    assert body["database"] == "postgres"
    for value in SECRETS.values():
        assert value not in response.text
    for fragment in ("SECRET", "internal.example", "redis://", "postgresql", "http"):
        assert fragment not in response.text
