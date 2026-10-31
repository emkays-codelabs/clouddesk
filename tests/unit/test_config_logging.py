"""Phase 1: settings and JSON logging (F14 settings hook, N3 log context)."""

import json
import logging

import pytest

from app.core.config import Settings, get_settings
from app.core.logging import JsonFormatter, log_context


def _format(message: str = "hello", **extra: object) -> dict:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))


class TestSettings:
    def test_reads_demo_mode_and_llm_provider_from_the_environment(self):
        settings = get_settings()

        assert settings.demo_mode is True
        assert settings.llm_provider == "fake"

    def test_environment_overrides_defaults(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        settings = get_settings()

        assert settings.demo_mode is False
        assert settings.llm_provider == "openai"

    def test_get_settings_is_cached(self):
        assert get_settings() is get_settings()

    def test_cors_origins_accepts_a_comma_separated_list(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://console.example.com")

        assert get_settings().cors_origins == [
            "http://localhost:3000",
            "https://console.example.com",
        ]

    def test_model_dump_redacts_secrets_and_url_passwords(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_API_KEY", "sk-super-secret")
        monkeypatch.setenv("JWT_SECRET", "jwt-super-secret")
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://app:hunter2@db.example.com/clouddesk"
        )

        dumped = json.dumps(get_settings().model_dump())

        assert "sk-super-secret" not in dumped
        assert "jwt-super-secret" not in dumped
        assert "hunter2" not in dumped
        assert "db.example.com" in dumped

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

    def test_defaults_match_the_offline_demo_profile(self):
        settings = Settings(_env_file=None)

        assert settings.demo_mode is True
        assert settings.llm_provider == "fake"
        assert settings.vector_store == "memory"
        assert settings.approval_required_for_refunds is True
        assert settings.max_refund_without_approval == 0
        assert settings.qdrant_collection == "clouddesk_knowledge"


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

    def test_nested_log_context_only_overrides_what_it_sets(self):
        with log_context(request_id="req-1"):
            with log_context(workflow_id="wf-2"):
                line = _format()

        assert line["request_id"] == "req-1"
        assert line["workflow_id"] == "wf-2"

    def test_line_carries_level_logger_message_and_timestamp(self):
        line = _format("something happened")

        assert line["level"] == "INFO"
        assert line["logger"] == "test"
        assert line["message"] == "something happened"
        assert "timestamp" in line

    def test_exception_info_is_included(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "t", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
            )

        line = json.loads(JsonFormatter().format(record))

        assert "ValueError: boom" in line["exception"]
