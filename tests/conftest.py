"""Offline test harness (F14): no network, no API key, throwaway data.

The environment is fixed at import time, before any test module imports `app`, so settings and
the app factory always see the offline profile, even if a developer has real keys exported.
"""

import ipaddress
import os
import socket
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_DATA_DIR = Path(tempfile.mkdtemp(prefix="clouddesk-tests-"))

OFFLINE_ENV = {
    "DEMO_MODE": "true",
    "ENVIRONMENT": "test",
    "LLM_PROVIDER": "fake",
    "VECTOR_STORE": "memory",
    "USE_FAKE_REDIS": "true",
    "DATABASE_URL": f"sqlite+aiosqlite:///{(_DATA_DIR / 'test.db').as_posix()}",
    "CHECKPOINT_DB_PATH": ":memory:",
    # Blank every credential so a key exported in the developer's shell cannot reach a test.
    "LLM_API_KEY": "",
    "QDRANT_API_KEY": "",
    "LANGCHAIN_API_KEY": "",
    "LANGCHAIN_TRACING_V2": "false",
    "SUPABASE_JWT_SECRET": "",
}
os.environ.update(OFFLINE_ENV)

from app.core.config import get_settings  # noqa: E402  (must follow the environment setup above)

_LOCAL_NAMES = {"", "localhost", "127.0.0.1", "::1"}


def _is_local(host: object) -> bool:
    """Loopback only: local servers and the event loop's own socket pair must keep working."""
    if host is None or isinstance(host, int):
        return True
    text = host.decode() if isinstance(host, bytes) else str(host)
    if text in _LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


@pytest.fixture(scope="session", autouse=True)
def _block_outside_network() -> Iterator[None]:
    """Turn any attempt to reach a non-local host into an immediate, explicit failure."""
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def blocked(host: object) -> RuntimeError:
        return RuntimeError(f"network access is disabled in tests (tried to reach {host!r})")

    def getaddrinfo(host, *args, **kwargs):
        if not _is_local(host):
            raise blocked(host)
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self, address):
        if isinstance(address, tuple) and not _is_local(address[0]):
            raise blocked(address[0])
        return real_connect(self, address)

    def connect_ex(self, address):
        if isinstance(address, tuple) and not _is_local(address[0]):
            raise blocked(address[0])
        return real_connect_ex(self, address)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket, "getaddrinfo", getaddrinfo)
        patch.setattr(socket.socket, "connect", connect)
        patch.setattr(socket.socket, "connect_ex", connect_ex)
        yield


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    """get_settings() is cached; clear it around every test so env changes are always seen."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> "Iterator[TestClient]":
    """A test client for the real app. Imported lazily so the harness can exist before the app."""
    app_main = pytest.importorskip("app.main", reason="the app does not exist until task P1-2")
    from fastapi.testclient import TestClient

    # raise_server_exceptions=False so a crashing route returns its real 500 response.
    with TestClient(app_main.create_app(), raise_server_exceptions=False) as test_client:
        yield test_client
