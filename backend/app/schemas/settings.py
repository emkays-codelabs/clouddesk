"""Redacted settings view (docs/design/06_API_CONTRACT.md, Settings).

Deliberately has no field that could hold a key, a URL or a password.
"""

from typing import Literal

from pydantic import BaseModel


class LlmSettings(BaseModel):
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    api_key_configured: bool
    tracing: bool


class ApprovalPolicy(BaseModel):
    refunds_require_approval: bool
    max_refund_without_approval: float
    approval_required_tools: list[str]


class SettingsView(BaseModel):
    demo_mode: bool
    environment: str
    llm: LlmSettings
    vector_store: str
    redis: Literal["real", "fake"]
    database: Literal["sqlite", "postgres"]
    approval_policy: ApprovalPolicy
