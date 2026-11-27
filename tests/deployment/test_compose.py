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


def test_the_five_services_exist():
    assert set(SERVICES) == {"frontend", "backend", "postgres", "redis", "qdrant"}


@pytest.mark.parametrize("name", ["frontend", "backend", "postgres", "redis", "qdrant"])
def test_every_service_restarts_and_has_a_healthcheck(name):
    assert SERVICES[name]["restart"] == "unless-stopped"
    assert SERVICES[name]["healthcheck"]["test"]


@pytest.mark.parametrize(
    ("service", "needs"),
    [("frontend", {"backend"}), ("backend", {"postgres", "redis", "qdrant"})],
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
    assert "pg_isready" in flat["postgres"]
    assert "/dev/tcp" in flat["qdrant"]


def test_named_volumes_are_declared_and_mounted():
    declared = set(COMPOSE["volumes"])
    mounted = {
        v.split(":")[0]
        for s in SERVICES.values()
        for v in s.get("volumes", [])
        if not v.startswith((".", "/"))
    }

    assert declared == {"backend-data", "postgres-data", "redis-data", "qdrant-storage"}
    assert mounted == declared


def test_ports_are_published_for_the_web_and_the_api():
    assert "${FRONTEND_PORT:-3000}:3000" in SERVICES["frontend"]["ports"]
    assert "${BACKEND_PORT:-8000}:8000" in SERVICES["backend"]["ports"]


def test_build_contexts_and_dockerfiles_exist():
    for name in ("frontend", "backend"):
        build = SERVICES[name]["build"]
        context = ROOT / build["context"]
        assert (context / build["dockerfile"]).is_file(), name
    assert SERVICES["backend"]["build"]["context"] == "."


def test_the_browser_facing_api_url_is_the_host_port():
    args = SERVICES["frontend"]["build"]["args"]

    assert args["NEXT_PUBLIC_API_URL"] == "http://localhost:${BACKEND_PORT:-8000}"


    """The Docker stack uses Postgres, Redis and Qdrant; SQLite and fakes are for offline tests."""
    """The Docker stack uses Postgres, Redis and Qdrant; SQLite and fakes are for offline tests."""
    env = SERVICES["backend"]["environment"]

    assert env["DEMO_MODE"] == "true"
    assert env["LLM_PROVIDER"] == "${LLM_PROVIDER:-fake}"  # the .env chooses the model provider
    assert env["VECTOR_STORE"] == "${VECTOR_STORE:-qdrant}"
    assert env["QDRANT_URL"] == "http://qdrant:6333"
    assert env["USE_FAKE_REDIS"] == "false"
    assert env["REDIS_URL"] == "redis://redis:6379/0"
    assert env["CORS_ORIGINS"] == "http://localhost:${FRONTEND_PORT:-3000}"
    assert env["DATABASE_URL"].startswith("postgresql+asyncpg://clouddesk:")
    assert env["DATABASE_URL"].endswith("@postgres:5432/clouddesk")
    assert env["CHECKPOINT_DB_PATH"].startswith("/app/data/")


def test_the_database_password_is_substituted_with_a_local_only_default():
    env = SERVICES["postgres"]["environment"]

    assert env["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD:-clouddesk-local}"
    assert env["POSTGRES_DB"] == "clouddesk"
    assert (
        "${POSTGRES_PASSWORD:-clouddesk-local}"
        in SERVICES["backend"]["environment"]["DATABASE_URL"]
    )


def test_postgres_keeps_its_data_on_a_named_volume():
    assert "postgres-data:/var/lib/postgresql/data" in SERVICES["postgres"]["volumes"]


# Passed from the host `.env` or environment by substitution. A machine without a key still comes up
# on the offline defaults (fake provider, empty models, 384 dimensions).
MODEL_SETTINGS = {
    "LLM_PROVIDER": "fake",
    "LLM_BASE_URL": "",
    "LLM_MODEL": "",
    "LLM_MODEL_FAST": "",
    "LLM_MODEL_SMART": "",
    "LLM_MODEL_REASONING": "",
    "EMBEDDING_PROVIDER": "fake",
    "EMBEDDING_MODEL": "",
    "EMBEDDING_BASE_URL": "",
    "EMBEDDING_DIMENSIONS": "384",
    "LLM_API_KEY": "",
}


@pytest.mark.parametrize("name,default", MODEL_SETTINGS.items())
def test_the_backend_receives_each_model_setting_with_an_offline_default(name, default):
    env = SERVICES["backend"]["environment"]

    assert env[name] == f"${{{name}:-{default}}}"


def test_the_api_key_is_substituted_never_written_into_the_file():
    assert SERVICES["backend"]["environment"]["LLM_API_KEY"] == "${LLM_API_KEY:-}"
    assert not re.search(r"(?im)^\s*\w*api_key:\s*['\"]?[^\s'\"$]", TEXT)
    assert not re.search(r"sk-[A-Za-z0-9]{8,}", TEXT)


def test_every_substituted_model_setting_is_a_real_settings_field():
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from app.core.config import Settings

    fields = {n.upper() for n in Settings.model_fields}

    assert set(MODEL_SETTINGS) <= fields


def test_host_ports_default_to_8000_and_3000_and_are_compose_only_variables():
    # Not read by Settings, so not listed in CLAUDE.md section 10.1 (test_env_settings).
    spec = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "BACKEND_PORT" not in spec.split("### 10.1")[1].split("### 10.2")[0]
    assert "FRONTEND_PORT" not in spec.split("### 10.1")[1].split("### 10.2")[0]
    assert "compose-only" in TEXT


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
