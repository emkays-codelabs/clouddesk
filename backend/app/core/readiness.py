from urllib.parse import urlsplit

from app.core.config import Settings
from app.schemas.health import CheckResult

_DATABASE_SCHEMES = {"sqlite+aiosqlite", "postgresql+asyncpg"}
_REDIS_SCHEMES = {"redis", "rediss", "unix"}


def _ok() -> CheckResult:
    return CheckResult(status="ok")


def _error(detail: str) -> CheckResult:
    # Details name the setting at fault but never echo a URL, password, or key.
    return CheckResult(status="error", detail=detail)


def _check_database(settings: Settings) -> CheckResult:
    scheme = urlsplit(settings.database_url).scheme
    if scheme in _DATABASE_SCHEMES:
        return _ok()
    return _error("DATABASE_URL is missing or uses an unsupported driver")


def _check_redis(settings: Settings) -> CheckResult:
    # No URL (or USE_FAKE_REDIS) means fakeredis, which needs no configuration.
    if settings.use_fake_redis or not settings.redis_url:
        return _ok()
    if urlsplit(settings.redis_url).scheme in _REDIS_SCHEMES:
        return _ok()
    return _error("REDIS_URL must start with redis://, rediss:// or unix://")


def _check_vector_store(settings: Settings) -> CheckResult:
    if settings.vector_store == "memory" or settings.qdrant_url:
        return _ok()
    return _error("QDRANT_URL is not set but VECTOR_STORE is qdrant")


def _check_llm(settings: Settings) -> CheckResult:
    if settings.llm_provider == "fake" or settings.llm_api_key.get_secret_value():
        return _ok()
    return _error("LLM_API_KEY is not set for the selected provider")


def check_readiness(settings: Settings) -> dict[str, CheckResult]:
    """Configuration probes only. They open no connection until later phases add the clients."""
    return {
        "database": _check_database(settings),
        "redis": _check_redis(settings),
        "vector_store": _check_vector_store(settings),
        "llm": _check_llm(settings),
    }
