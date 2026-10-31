"""P1-2: health probes and request ids (N3). See docs/API_CONTRACT.md, Health section."""

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

    def test_health_and_live_do_no_dependency_io(
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
        # Every URL below is invalid on purpose: a check only builds its detail text on failure,
        # so a valid URL would never exercise the code that could leak it.
        monkeypatch.setenv("DATABASE_URL", "mysql://app:hunter2@db.example.com/x")
        monkeypatch.setenv("USE_FAKE_REDIS", "false")
        monkeypatch.setenv("REDIS_URL", "ftp://:redis-pass@cache.example.com")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "")

        with TestClient(create_app()) as client:
            response = client.get("/health/ready")

        assert response.status_code == 503
        checks = response.json()["checks"]
        assert {name: c["status"] for name, c in checks.items()} == {
            "database": "error",
            "redis": "error",
            "vector_store": "error",
            "llm": "error",
        }  # all four failed, so all four detail strings were built and inspected below
        for secret in (
            "hunter2",
            "db.example.com",
            "qdrant-secret-key",
            "redis-pass",
            "cache.example.com",
        ):
            assert secret not in response.text

    @pytest.mark.parametrize(
        ("env", "check"),
        [
            ({"DATABASE_URL": "mysql://app@db/x"}, "database"),
            # fake Redis ignores the URL, so a real Redis has to be selected for it to matter
            ({"USE_FAKE_REDIS": "false", "REDIS_URL": "http://cache:6379"}, "redis"),
            ({"VECTOR_STORE": "qdrant"}, "vector_store"),
        ],
        ids=["unsupported-database", "bad-redis-scheme", "qdrant-without-url"],
    )
    def test_each_check_can_fail_on_its_own(
        self, monkeypatch: pytest.MonkeyPatch, env: dict[str, str], check: str
    ):
        for name, value in env.items():
            monkeypatch.setenv(name, value)

        with TestClient(create_app()) as client:
            body = client.get("/health/ready").json()

        assert body["checks"][check]["status"] == "error"
        others = {name: c["status"] for name, c in body["checks"].items() if name != check}
        assert set(others.values()) == {"ok"}

    def test_fake_redis_ignores_a_malformed_redis_url(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("USE_FAKE_REDIS", "true")
        monkeypatch.setenv("REDIS_URL", "http://cache:6379")

        with TestClient(create_app()) as client:
            body = client.get("/health/ready").json()

        assert body["checks"]["redis"]["status"] == "ok"


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
        ["has space", "semi;colon", "x" * 129, "naïve", "a/b", "bad\ttab"],
        ids=["space", "semicolon", "too-long", "non-ascii", "slash", "tab"],
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
        assert "unexpected failure" not in response.text

    def test_the_request_id_is_bound_to_log_lines_while_handling_the_request(
        self, capsys: pytest.CaptureFixture[str]
    ):
        import json
        import logging

        app = create_app()

        @app.get("/log-me")
        async def log_me() -> dict[str, str]:
            logging.getLogger("clouddesk.test").info("inside the request")
            return {"ok": "yes"}

        with TestClient(app) as client:
            client.get("/log-me", headers={"X-Request-ID": "req-from-test"})

        lines = [
            json.loads(line)
            for line in capsys.readouterr().out.splitlines()
            if line.startswith("{")
        ]
        mine = [line for line in lines if line["message"] == "inside the request"]
        assert mine and mine[0]["request_id"] == "req-from-test"


class TestCors:
    def test_cors_exposes_the_request_id_header(self, client: TestClient):
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert "x-request-id" in response.headers["access-control-expose-headers"].lower()

    def test_preflight_from_the_console_origin_is_allowed(self, client: TestClient):
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_an_unknown_origin_gets_no_cors_headers(self, client: TestClient):
        response = client.get("/health", headers={"Origin": "https://evil.example.com"})

        assert "access-control-allow-origin" not in response.headers
