"""P1-3: the offline test harness (F14: everything runs with no network and no API key)."""

import asyncio
import os
import socket
from pathlib import Path

import pytest

from app.core.config import get_settings

_session_loop_ids: list[int] = []


class TestOfflineEnvironment:
    def test_offline_profile_is_in_force(self):
        settings = get_settings()

        assert settings.demo_mode is True
        assert settings.llm_provider == "fake"
        assert settings.vector_store == "memory"
        assert settings.use_fake_redis is True
        assert settings.checkpoint_db_path == ":memory:"
        assert settings.environment == "test"

    @pytest.mark.parametrize(
        "name",
        [
            "DEMO_MODE",
            "ENVIRONMENT",
            "LLM_PROVIDER",
            "VECTOR_STORE",
            "USE_FAKE_REDIS",
            "DATABASE_URL",
            "CHECKPOINT_DB_PATH",
        ],
    )
    def test_every_offline_variable_is_set_explicitly(self, name: str):
        # Several of these equal the code defaults, so only an explicit setting survives a
        # developer exporting something different in their shell.
        assert name in os.environ

    def test_database_is_a_throwaway_sqlite_file_outside_the_project(self):
        url = get_settings().database_url
        path = Path(url.removeprefix("sqlite+aiosqlite:///"))

        assert url.startswith("sqlite+aiosqlite:///")
        assert "clouddesk-tests-" in str(path)
        assert Path.cwd() not in path.parents  # never the project's own data/ folder

    @pytest.mark.parametrize(
        "name", ["LLM_API_KEY", "QDRANT_API_KEY", "LANGCHAIN_API_KEY", "SUPABASE_JWT_SECRET"]
    )
    def test_no_api_key_reaches_the_tests(self, name: str):
        assert os.environ[name] == ""

    def test_tracing_is_off(self):
        assert get_settings().langchain_tracing_v2 is False

    def test_a_developers_exported_key_cannot_leak_in(self):
        # The harness sets these before collection, so a key exported in the shell is overridden.
        assert get_settings().llm_api_key.get_secret_value() == ""

    def test_settings_follow_env_changes_after_cache_clear(self, monkeypatch: pytest.MonkeyPatch):
        assert get_settings().llm_provider == "fake"

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        get_settings.cache_clear()

        assert get_settings().llm_provider == "openai"

    def test_each_test_starts_from_the_offline_profile_again(self):
        assert get_settings().llm_provider == "fake"  # the change above did not leak


class TestNetworkGuard:
    def test_a_name_lookup_for_an_outside_host_is_blocked(self):
        with pytest.raises(RuntimeError, match="network access is disabled"):
            socket.getaddrinfo("example.com", 443)

    def test_a_connection_to_an_outside_address_is_blocked(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(RuntimeError, match="network access is disabled"):
                sock.connect(("93.184.216.34", 80))
        finally:
            sock.close()

    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
    def test_loopback_still_works_so_local_servers_and_event_loops_are_unaffected(self, host: str):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = server.getsockname()[1]
            with socket.create_connection((host, port), timeout=2) as client:
                conn, _ = server.accept()
                with conn:
                    client.sendall(b"ping")
                    assert conn.recv(4) == b"ping"


class TestAsyncSupport:
    async def test_async_tests_run_without_a_marker(self):
        await asyncio.sleep(0)

        assert asyncio.get_running_loop().is_running()

    async def test_first_test_records_the_loop(self):
        _session_loop_ids.append(id(asyncio.get_running_loop()))

    async def test_later_tests_share_that_same_session_loop(self):
        _session_loop_ids.append(id(asyncio.get_running_loop()))

        assert len(set(_session_loop_ids)) == 1
