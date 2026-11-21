"""Redacted view of the running configuration. Reports facts, never values that grant access."""

from app.core.config import get_settings
from app.schemas.settings import ApprovalPolicy, LlmSettings, SettingsView

# CLAUDE.md 7.4. Moves to the ToolRegistry policy when that lands (Phase 6).
APPROVAL_REQUIRED_TOOLS = ["create_refund_request", "reset_demo_setting"]


def get_settings_view() -> SettingsView:
    s = get_settings()
    return SettingsView(
        demo_mode=s.demo_mode,
        environment=s.environment,
        llm=LlmSettings(
            llm_provider=s.llm_provider,
            llm_model=s.llm_model,
            embedding_provider=s.embedding_provider,
            embedding_model=s.embedding_model,
            api_key_configured=bool(s.llm_api_key.get_secret_value()),
            tracing=s.langchain_tracing_v2,
        ),
        vector_store=s.vector_store,
        redis="fake" if s.use_fake_redis or not s.redis_url else "real",
        database="sqlite" if s.database_url.startswith("sqlite") else "postgres",
        approval_policy=ApprovalPolicy(
            refunds_require_approval=s.approval_required_for_refunds,
            max_refund_without_approval=s.max_refund_without_approval,
            approval_required_tools=list(APPROVAL_REQUIRED_TOOLS),
        ),
    )
