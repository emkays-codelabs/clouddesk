"""P1-1: settings and JSON logging (F14 settings hook; request_id / workflow_id log context)."""

import json
import logging
import sys

import pytest

from app.core.config import Settings, get_settings, redact_url
from app.core.logging import JsonFormatter, log_context, setup_logging


@pytest.fixture(autouse=True)
def _hermetic_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """No ambient variables, no local .env file, and a fresh settings cache for every test."""
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)
    monkeypatch.chdir(tmp_path)  # a developer's own .env in the repo root must not leak in
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _format(message: str = "hello") -> dict:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, message, None, None)
    return json.loads(JsonFormatter().format(record))


class TestSettings:
    def test_reads_demo_mode_and_llm_provider_from_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        settings = get_settings()

        assert settings.demo_mode is False
        assert settings.llm_provider == "openai"

    def test_defaults_describe_the_offline_demo_profile(self):
        settings = get_settings()

        assert settings.demo_mode is True
        assert settings.llm_provider == "fake"
        assert settings.vector_store == "memory"
        assert settings.approval_required_for_refunds is True
        assert settings.max_refund_without_approval == 0
        assert settings.qdrant_collection == "clouddesk_knowledge"
        assert settings.rate_limit_per_minute == 120

    def test_get_settings_is_cached_until_cleared(self, monkeypatch: pytest.MonkeyPatch):
        first = get_settings()
        monkeypatch.setenv("ENVIRONMENT", "changed")

        assert get_settings() is first
        assert get_settings().environment != "changed"

        get_settings.cache_clear()
        assert get_settings().environment == "changed"

    def test_cors_origins_accepts_a_comma_separated_list(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://console.example.com")

        assert get_settings().cors_origins == [
            "http://localhost:3000",
            "https://console.example.com",
        ]

    def test_cors_origins_accepts_a_json_list(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", '["https://a.example.com"]')

        assert get_settings().cors_origins == ["https://a.example.com"]

    def test_an_unknown_vector_store_fails_fast(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("VECTOR_STORE", "chroma")

        with pytest.raises(ValueError):
            get_settings()

    def test_values_come_from_a_local_env_file(self, tmp_path):
        (tmp_path / ".env").write_text("LLM_PROVIDER=anthropic\n", encoding="utf-8")

        assert Settings().llm_provider == "anthropic"


class TestRedaction:
    def test_model_dump_hides_secrets_and_url_passwords(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-super-secret")
        monkeypatch.setenv("JWT_SECRET", "jwt-super-secret")
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://app:hunter2@db.example.com/clouddesk"
        )

        dumped = json.dumps(get_settings().model_dump())

        assert "sk-super-secret" not in dumped
        assert "jwt-super-secret" not in dumped
        assert "hunter2" not in dumped
        assert "app:***@db.example.com" in dumped  # user and host stay, for diagnostics

    def test_attributes_still_expose_real_values_to_connection_code(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("LLM_API_KEY", "sk-super-secret")
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://app:hunter2@db.example.com/clouddesk"
        )

        settings = get_settings()

        assert settings.llm_api_key.get_secret_value() == "sk-super-secret"
        assert "hunter2" in settings.database_url

    def test_an_unset_secret_dumps_as_empty_not_as_masked(self):
        assert get_settings().model_dump()["llm_api_key"] == ""

    def test_a_url_without_a_password_is_left_alone(self):
        assert get_settings().model_dump()["database_url"].startswith("sqlite+aiosqlite:///")


class TestJsonLogging:
    def test_every_line_has_request_id_and_workflow_id_null_when_unset(self):
        line = _format()

        assert line["request_id"] is None
        assert line["workflow_id"] is None

    def test_log_context_binds_ids_and_restores_them_afterwards(self):
        with log_context(request_id="req-1", workflow_id="wf-9"):
            inside = _format()
        after = _format()

        assert inside["request_id"] == "req-1"
        assert inside["workflow_id"] == "wf-9"
        assert after["request_id"] is None
        assert after["workflow_id"] is None

    def test_nested_log_context_only_overrides_what_it_sets(self):
        with log_context(request_id="req-1"):
            with log_context(workflow_id="wf-2"):
                inner = _format()
            outer = _format()

        assert inner["request_id"] == "req-1"
        assert inner["workflow_id"] == "wf-2"
        assert outer["workflow_id"] is None

    def test_log_context_restores_ids_even_when_the_block_raises(self):
        with pytest.raises(RuntimeError):
            with log_context(request_id="req-1"):
                raise RuntimeError("boom")

        assert _format()["request_id"] is None

    def test_line_carries_level_logger_message_and_timestamp(self):
        line = _format("something happened")

        assert line["level"] == "INFO"
        assert line["logger"] == "test"
        assert line["message"] == "something happened"
        assert line["timestamp"].endswith("+00:00")

    def test_exception_info_is_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord(
                "t", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
            )

        line = json.loads(JsonFormatter().format(record))

        assert "ValueError: boom" in line["exception"]


class TestRedactUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            (
                "postgresql+asyncpg://app:hunter2@db.example.com/x",
                "postgresql+asyncpg://app:***@db.example.com/x",
            ),
            ("redis://:hunter2@cache.example.com:6379/0", "redis://:***@cache.example.com:6379/0"),
            (
                "https://u:p%40ss@host.example.com:8443/path?q=1",
                "https://u:***@host.example.com:8443/path?q=1",
            ),
        ],
        ids=["user-and-password", "password-only", "port-query-and-encoded-password"],
    )
    def test_masks_only_the_password(self, url: str, expected: str):
        assert redact_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "sqlite+aiosqlite:///./data/support.db",
            "redis://cache.example.com:6379/0",
            "",
            "not a url",
        ],
        ids=["sqlite-file", "no-credentials", "empty", "not-a-url"],
    )
    def test_leaves_urls_without_a_password_unchanged(self, url: str):
        assert redact_url(url) == url


class TestSetupLogging:
    @pytest.fixture(autouse=True)
    def _restore_logging_state(self):
        """setup_logging() edits global loggers; put them back so other tests are unaffected."""
        root = logging.getLogger()
        names = ("uvicorn", "uvicorn.error", "uvicorn.access")
        saved_root = (list(root.handlers), root.level)
        saved = {
            n: (list(logging.getLogger(n).handlers), logging.getLogger(n).propagate) for n in names
        }
        yield
        root.handlers[:] = saved_root[0]
        root.setLevel(saved_root[1])
        for n, (handlers, propagate) in saved.items():
            logging.getLogger(n).handlers[:] = handlers
            logging.getLogger(n).propagate = propagate

    @staticmethod
    def _json_handlers() -> list[logging.Handler]:
        return [h for h in logging.getLogger().handlers if isinstance(h.formatter, JsonFormatter)]

    def test_writes_json_lines_with_the_bound_ids_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ):
        setup_logging()

        with log_context(request_id="req-7", workflow_id="wf-3"):
            logging.getLogger("clouddesk.test").info("hello from a request")

        line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert line["message"] == "hello from a request"
        assert line["logger"] == "clouddesk.test"
        assert line["request_id"] == "req-7"
        assert line["workflow_id"] == "wf-3"

    def test_is_idempotent_and_installs_exactly_one_json_handler(self):
        setup_logging()
        setup_logging()
        setup_logging()

        assert len(self._json_handlers()) == 1

    def test_leaves_handlers_it_did_not_install_alone(self):
        foreign = logging.NullHandler()
        logging.getLogger().addHandler(foreign)

        setup_logging()

        assert foreign in logging.getLogger().handlers

    def test_applies_the_requested_level(self, capsys: pytest.CaptureFixture[str]):
        setup_logging("WARNING")

        logging.getLogger("clouddesk.test").info("quiet")
        logging.getLogger("clouddesk.test").warning("loud")

        out = capsys.readouterr().out
        assert "loud" in out
        assert "quiet" not in out

    def test_hands_uvicorn_records_to_the_json_handler(self, capsys: pytest.CaptureFixture[str]):
        uvicorn_logger = logging.getLogger("uvicorn.access")
        uvicorn_logger.addHandler(logging.NullHandler())
        uvicorn_logger.propagate = False

        setup_logging()

        assert uvicorn_logger.handlers == []
        assert uvicorn_logger.propagate is True
        uvicorn_logger.info("GET /health 200")
        assert (
            json.loads(capsys.readouterr().out.strip().splitlines()[-1])["logger"]
            == "uvicorn.access"
        )
