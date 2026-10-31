"""P1-4: .env.example lists every variable in CLAUDE.md section 10.1, with placeholders only."""

from pathlib import Path

from app.core.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"

# Copied from CLAUDE.md section 10.1. Update both together when a variable is added.
SPEC_VARIABLES = {
    "DEMO_MODE", "ENVIRONMENT", "CORS_ORIGINS", "JWT_SECRET", "SUPABASE_JWT_SECRET",
    "DATABASE_URL", "CHECKPOINT_DB_PATH", "REDIS_URL", "USE_FAKE_REDIS",
    "LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL",
    "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "EMBEDDING_DIMENSIONS",
    "VECTOR_STORE", "QDRANT_URL", "QDRANT_API_KEY", "QDRANT_COLLECTION",
    "APPROVAL_REQUIRED_FOR_REFUNDS", "MAX_REFUND_WITHOUT_APPROVAL",
    "TOOL_TIMEOUT_SECONDS", "RATE_LIMIT_PER_MINUTE", "SAMPLE_DATA_DIR",
    "LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT",
}  # fmt: skip

SECRET_VARIABLES = ("LLM_API_KEY", "QDRANT_API_KEY", "LANGCHAIN_API_KEY", "SUPABASE_JWT_SECRET")


def _declared_variables() -> dict[str, str]:
    values = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip()
    return values


def test_env_example_lists_every_variable_in_the_spec():
    assert SPEC_VARIABLES - _declared_variables().keys() == set()


def test_env_example_covers_every_settings_field():
    fields = {name.upper() for name in Settings.model_fields}

    assert fields - _declared_variables().keys() == set()


def test_env_example_declares_nothing_the_application_does_not_read():
    fields = {name.upper() for name in Settings.model_fields}

    assert _declared_variables().keys() - fields == set()


def test_env_example_loads_into_settings_without_errors(monkeypatch):
    for name, value in _declared_variables().items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert settings.demo_mode is True
    assert settings.llm_provider == "fake"
    assert settings.vector_store == "memory"


def test_env_example_holds_placeholders_not_real_keys():
    declared = _declared_variables()

    for name in SECRET_VARIABLES:
        assert declared[name] == "", f"{name} must be empty in the committed example"


def test_the_only_non_empty_secret_is_an_obvious_demo_placeholder():
    assert "change-me" in _declared_variables()["JWT_SECRET"]


def test_each_variable_is_declared_once():
    lines = [
        line.partition("=")[0].strip()
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    ]

    assert len(lines) == len(set(lines))
