"""P14-3: static checks on docker-compose.yml (N8).

These parse the file. They do NOT prove the stack comes up healthy: that needs a Docker daemon.
"""

import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEXT = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
COMPOSE = yaml.safe_load(TEXT)
SERVICES = COMPOSE["services"]


def test_the_project_is_named_clouddesk():
    assert COMPOSE["name"] == "clouddesk"


def test_the_four_services_exist():
    assert set(SERVICES) == {"frontend", "backend", "redis", "qdrant"}


@pytest.mark.parametrize("name", ["frontend", "backend", "redis", "qdrant"])
def test_every_service_restarts_and_has_a_healthcheck(name):
    assert SERVICES[name]["restart"] == "unless-stopped"
    assert SERVICES[name]["healthcheck"]["test"]


@pytest.mark.parametrize(
    ("service", "needs"),
    [("frontend", {"backend"}), ("backend", {"redis", "qdrant"})],
)
def test_dependencies_wait_for_healthy(service, needs):
    depends = SERVICES[service]["depends_on"]

    assert set(depends) == needs
    assert all(v == {"condition": "service_healthy"} for v in depends.values())


def test_the_healthchecks_probe_the_documented_endpoints():
    flat = {n: " ".join(map(str, s["healthcheck"]["test"])) for n, s in SERVICES.items()}

    assert "/health/live" in flat["backend"]
    assert "/api/health" in flat["frontend"]
    assert "redis-cli ping" in flat["redis"]
    assert "/dev/tcp" in flat["qdrant"]


def test_named_volumes_are_declared_and_mounted():
    declared = set(COMPOSE["volumes"])
    mounted = {
        v.split(":")[0]
        for s in SERVICES.values()
        for v in s.get("volumes", [])
        if not v.startswith((".", "/"))
    }

    assert declared == {"backend-data", "redis-data", "qdrant-storage"}
    assert mounted == declared


def test_ports_are_published_for_the_web_and_the_api():
    assert "3000:3000" in SERVICES["frontend"]["ports"]
    assert "8000:8000" in SERVICES["backend"]["ports"]


def test_build_contexts_and_dockerfiles_exist():
    for name in ("frontend", "backend"):
        build = SERVICES[name]["build"]
        context = ROOT / build["context"]
        assert (context / build["dockerfile"]).is_file(), name
    assert SERVICES["backend"]["build"]["context"] == "."


def test_the_browser_facing_api_url_is_the_host_port():
    args = SERVICES["frontend"]["build"]["args"]

    assert args["NEXT_PUBLIC_API_URL"] == "http://localhost:8000"


def test_the_backend_runs_the_offline_demo_defaults():
    env = SERVICES["backend"]["environment"]

    assert env["DEMO_MODE"] == "true"
    assert env["LLM_PROVIDER"] == "fake"
    assert env["VECTOR_STORE"] == "memory"
    assert env["USE_FAKE_REDIS"] == "false"
    assert env["REDIS_URL"] == "redis://redis:6379/0"
    assert env["CORS_ORIGINS"] == "http://localhost:3000"
    assert env["DATABASE_URL"].endswith("//app/data/support.db")
    assert env["CHECKPOINT_DB_PATH"].startswith("/app/data/")


def test_the_data_directory_is_a_named_volume():
    assert "backend-data:/app/data" in SERVICES["backend"]["volumes"]


def test_images_are_pinned_to_a_tag_not_latest():
    for name in ("redis", "qdrant"):
        image = SERVICES[name]["image"]
        assert ":" in image and not image.endswith(":latest"), image
    assert "pin by digest before production" in TEXT


def test_env_file_is_optional():
    entry = SERVICES["backend"]["env_file"][0]

    assert entry == {"path": ".env", "required": False}


def test_no_secret_literals():
    secret = re.compile(
        r"(?i)^\s*\w*(api_key|secret|password|token)\w*\s*:\s*['\"]?[^\s'\"$][^\s'\"]*"
    )
    hits = [ln for ln in TEXT.splitlines() if not ln.strip().startswith("#") and secret.search(ln)]

    assert hits == []
    assert "${JWT_SECRET:-change-me-demo-only}" in TEXT
