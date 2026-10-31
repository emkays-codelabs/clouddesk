"""Phase 1: health probes and request ids (N3, F14). See docs/API_CONTRACT.md, Health section."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app


def _app_with_crashing_route() -> FastAPI:
    app = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected failure")

    return app


class TestHealth:
    def test_health_reports_service_version_and_environment(self, client: TestClient):
        response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["environment"] == "test"
        assert body["service"]
        assert body["version"]

    def test_live_is_a_bare_alive_response(self, client: TestClient):
        response = client.get("/health/live")

        assert response.status_code == 200
        assert response.json() == {"status": "alive"}

    def test_live_and_health_do_no_dependency_io(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        def fail(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("readiness checks must not run for /health or /health/live")

        monkeypatch.setattr("app.api.health.check_readiness", fail)

        assert client.get("/health").status_code == 200
        assert client.get("/health/live").status_code == 200

    def test_ready_is_200_with_all_four_checks_ok_offline(self, client: TestClient):
        response = client.get("/health/ready")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert set(body["checks"]) == {"database", "redis", "vector_store", "llm"}
        assert all(check["status"] == "ok" for check in body["checks"].values())

    def test_ready_is_503_degraded_when_a_check_fails(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "")

        with TestClient(create_app()) as client:
            response = client.get("/health/ready")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert body["checks"]["llm"]["status"] == "error"
        assert body["checks"]["llm"]["detail"]
        assert body["checks"]["database"]["status"] == "ok"

    def test_ready_details_never_leak_urls_passwords_or_keys(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("VECTOR_STORE", "qdrant")
        monkeypatch.setenv("QDRANT_URL", "")
        monkeypatch.setenv("QDRANT_API_KEY", "qdrant-secret-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app:hunter2@db.example.com/x")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "")

        with TestClient(create_app()) as client:
            text = client.get("/health/ready").text

        assert "hunter2" not in text
        assert "db.example.com" not in text
        assert "qdrant-secret-key" not in text


class TestRequestId:
    @pytest.mark.parametrize("path", ["/health", "/health/live", "/health/ready", "/missing"])
    def test_every_response_carries_a_request_id(self, client: TestClient, path: str):
        response = client.get(path)

        assert response.headers["X-Request-ID"]

    def test_a_safe_caller_supplied_id_is_echoed(self, client: TestClient):
        response = client.get("/health", headers={"X-Request-ID": "abc-123_DEF.456:7"})

        assert response.headers["X-Request-ID"] == "abc-123_DEF.456:7"

    @pytest.mark.parametrize(
        "unsafe",
        ["has space", "semi;colon", "x" * 129, "naïve", "a/b"],
        ids=["space", "semicolon", "too-long", "non-ascii", "slash"],
    )
    def test_an_unsafe_caller_supplied_id_is_replaced_with_a_uuid(
        self, client: TestClient, unsafe: str
    ):
        response = client.get("/health", headers={"X-Request-ID": unsafe.encode("utf-8")})

        issued = response.headers["X-Request-ID"]
        assert issued != unsafe
        assert len(issued) == 36 and issued.count("-") == 4

    def test_a_missing_id_gets_a_fresh_uuid_each_time(self, client: TestClient):
        first = client.get("/health").headers["X-Request-ID"]
        second = client.get("/health").headers["X-Request-ID"]

        assert first != second

    def test_the_boundary_length_of_128_is_accepted(self, client: TestClient):
        value = "a" * 128

        response = client.get("/health", headers={"X-Request-ID": value})

        assert response.headers["X-Request-ID"] == value

    def test_an_unhandled_error_returns_500_with_a_request_id_and_no_internals(self):
        with TestClient(_app_with_crashing_route(), raise_server_exceptions=False) as client:
            response = client.get("/boom", headers={"X-Request-ID": "trace-me"})

        assert response.status_code == 500
        assert response.headers["X-Request-ID"] == "trace-me"
        assert response.json() == {"detail": "Internal Server Error"}


class TestCors:
    def test_cors_exposes_the_request_id_header(self, client: TestClient):
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "x-request-id" in response.headers["access-control-expose-headers"].lower()

    def test_preflight_from_the_console_origin_is_allowed(self, client: TestClient):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
