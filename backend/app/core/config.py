import json
from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REDACTED = "***"


def redact_url(url: str) -> str:
    """Mask the password in a connection URL, keeping user and host for diagnostics."""
    parts = urlsplit(url)
    if parts.password is None:
        return url
    host = parts.netloc.rpartition("@")[2]
    return urlunsplit(parts._replace(netloc=f"{parts.username or ''}:{REDACTED}@{host}"))


class Settings(BaseSettings):
    """Process configuration; the variables are listed in CLAUDE.md section 10.1 (values: .env)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Runtime
    demo_mode: bool = True
    environment: str = "development"
    # NoDecode: pydantic-settings would otherwise demand JSON for a list; we accept "a,b".
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Auth
    jwt_secret: SecretStr = SecretStr("change-me-demo-only")
    supabase_jwt_secret: SecretStr = SecretStr("")

    # Storage
    database_url: str = "sqlite+aiosqlite:///./data/support.db"
    checkpoint_db_path: str = "./data/checkpoints.db"
    redis_url: str = ""
    use_fake_redis: bool = False

    # LLM and embeddings
    llm_provider: str = "fake"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    llm_base_url: str = ""
    # Tier models for the Euron router (P9-9); each falls back to llm_model, then the tier default.
    llm_model_fast: str = ""
    llm_model_smart: str = ""
    llm_model_reasoning: str = ""
    # Verified prices only: JSON {"model": [usd_per_million_input, usd_per_million_output]}.
    # Empty means unknown, and a call is then reported as cost unavailable, never as zero.
    llm_pricing: str = ""
    embedding_provider: str = "fake"
    embedding_model: str = ""
    embedding_base_url: str = ""  # P9-10: empty falls back to llm_base_url
    embedding_dimensions: int = 384

    # Vector store
    vector_store: Literal["memory", "qdrant"] = "memory"
    qdrant_url: str = ""
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_collection: str = "clouddesk_knowledge"

    # Policy and limits
    approval_required_for_refunds: bool = True
    max_refund_without_approval: float = 0
    tool_timeout_seconds: float = 30
    rate_limit_per_minute: int = 120
    sample_data_dir: str = "./sample_data"

    # Observability
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr = SecretStr("")
    langchain_project: str = "clouddesk-support"

    @property
    def effective_jwt_secret(self) -> str:
        """The key tokens are signed and checked with: Supabase's when set, else the local one."""
        return self.supabase_jwt_secret.get_secret_value() or self.jwt_secret.get_secret_value()

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Redacted view, safe to log or return. Connection code reads attributes, not this."""
        data = super().model_dump(**kwargs)
        for name, value in data.items():
            if isinstance(value, SecretStr):
                data[name] = REDACTED if value.get_secret_value() else ""
            elif name.endswith("_url") and isinstance(value, str):
                data[name] = redact_url(value)
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
