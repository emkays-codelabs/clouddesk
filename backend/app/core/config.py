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
    """Process configuration. Every variable is documented in .env.example."""

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
    embedding_provider: str = "fake"
    embedding_model: str = ""
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
