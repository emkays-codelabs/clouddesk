"""N2: fixed-window rate limit per client, backed by (fake) Redis."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.redis import get_redis
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import HEADER, RequestIdMiddleware


class Clock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def build(limit: int, clock: Clock) -> TestClient:
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(RateLimitMiddleware, limit=limit, clock=clock)
    app.add_middleware(RequestIdMiddleware)
    return TestClient(app)


def test_request_after_the_limit_is_429_with_retry_after_and_request_id():
    c = build(2, Clock())
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 200
    blocked = c.get("/ping", headers={HEADER: "abc-123"})
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many requests"}
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60
    assert blocked.headers[HEADER] == "abc-123"


def test_limit_resets_in_the_next_window():
    clock = Clock(1_000_020.0)
    c = build(1, clock)
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 429
    clock.now += 60
    assert c.get("/ping").status_code == 200


def test_clients_are_counted_separately():
    c = build(1, Clock())
    assert c.get("/ping", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    # The limiter keys on the socket peer, not a spoofable header, so this is the same client.
    assert c.get("/ping", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_health_probes_are_exempt():
    c = build(1, Clock())
    for _ in range(5):
        assert c.get("/health/live").status_code == 200
    assert c.get("/ping").status_code == 200


def test_redis_outage_fails_open(monkeypatch: pytest.MonkeyPatch):
    class Broken:
        async def incr(self, *_a):
            raise ConnectionError("down")

    monkeypatch.setattr("app.middleware.rate_limit.get_redis", lambda: Broken())
    c = build(1, Clock())
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 200


def test_app_enforces_the_configured_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    from app.main import create_app

    with TestClient(create_app()) as c:
        codes = [c.get("/api/v1/auth/me").status_code for _ in range(3)]
        assert codes[:2] == [401, 401]
        assert codes[2] == 429
        # CORS is outermost, so even a 429 carries the CORS and request-id headers.
        r = c.get("/api/v1/auth/me", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 429
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert HEADER in r.headers
        assert c.get("/health/live").status_code == 200


def test_fake_redis_is_used_when_url_empty_and_is_cached():
    first = get_redis()
    assert get_redis() is first
    assert type(first).__module__.startswith("fakeredis")
