"""Offline test harness.

The environment is fixed before `app` is imported, so settings, the logger and the app factory all
see the offline configuration: fake LLM, in-memory vector store, fakeredis, throwaway SQLite.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_DATA_DIR = Path(tempfile.mkdtemp(prefix="clouddesk-tests-"))

os.environ.update(
    {
        "DEMO_MODE": "true",
        "ENVIRONMENT": "test",
        "LLM_PROVIDER": "fake",
        "VECTOR_STORE": "memory",
        "USE_FAKE_REDIS": "true",
        "DATABASE_URL": f"sqlite+aiosqlite:///{_DATA_DIR / 'test.db'}",
        "CHECKPOINT_DB_PATH": ":memory:",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    """get_settings() is cached; clear it so a test that changes env vars sees them."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    # raise_server_exceptions=False so a crashing route returns the real 500 response.
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
