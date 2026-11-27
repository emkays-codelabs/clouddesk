"""QA defect: real Euron runs reported $0.0000 because no price is verified for their models.

A cost is one of: `actual` (the provider reported it), `estimated` (a price the owner configured in
LLM_PRICING), `unavailable` (tokens were used but no verified price exists) or `none` (no model
was called). Unknown is never shown as zero, and no price is invented.
"""

import json

from agents.state import merge_usage
from app.core.config import Settings
from app.core.llm import Completion, FakeProvider, call_structured, configured_cost
from app.schemas.workflow import Classification, TokenUsage

REPLY = json.dumps({"category": "billing", "summary": "s"})


class _Provider:
    """A provider that knows no price, like Euron today."""

    name, model = "euron", "euri-chat-fast"

    def __init__(self, reported=None):
        self.reported = reported

    def estimate_cost(self, p, c):
        return None

    async def complete(self, schema, messages, temperature, hints):
        done = Completion(REPLY, 1000, 500)
        done.model = "euri-chat-fast"
        done.reported_cost_usd = self.reported
        return done


async def test_a_provider_reported_cost_is_actual():
    r = await call_structured(Classification, system="s", user="u", llm=_Provider(reported=0.0123))
    assert r.usage.cost_basis == "actual"
    assert r.usage.estimated_cost_usd == 0.0123


async def test_a_configured_price_gives_a_transparent_estimate(monkeypatch):
    monkeypatch.setattr(
        "app.core.llm.get_settings",
        lambda: Settings(llm_pricing=json.dumps({"euri-chat-fast": [1.0, 2.0]})),
    )
    r = await call_structured(Classification, system="s", user="u", llm=_Provider())
    assert r.usage.cost_basis == "estimated"
    assert r.usage.estimated_cost_usd == (1000 * 1.0 + 500 * 2.0) / 1_000_000


async def test_tokens_without_any_price_are_unavailable_not_zero(monkeypatch):
    monkeypatch.setattr("app.core.llm.get_settings", lambda: Settings(llm_pricing=""))
    r = await call_structured(Classification, system="s", user="u", llm=_Provider())
    assert r.usage.total_tokens == 1500, "token usage is still recorded"
    assert r.usage.cost_basis == "unavailable"


async def test_the_offline_fake_provider_costs_nothing_and_says_so():
    r = await call_structured(Classification, system="s", user="u", llm=FakeProvider())
    assert r.usage.estimated_cost_usd == 0.0
    assert r.usage.cost_basis == "estimated"


def test_configured_cost_ignores_bad_or_missing_pricing():
    assert configured_cost("m", 10, 10, "") is None
    assert configured_cost("m", 10, 10, "not json") is None
    assert configured_cost("m", 10, 10, json.dumps({"other": [1, 2]})) is None
    assert configured_cost("m", 10, 10, json.dumps({"m": [1]})) is None
    assert configured_cost("m", 10, 10, json.dumps({"m": [-1, 2]})) is None
    assert configured_cost("m", 1_000_000, 0, json.dumps({"m": [3, 4]})) == 3.0


def _u(basis, cost=0.0, tokens=10):
    return TokenUsage(total_tokens=tokens, estimated_cost_usd=cost, cost_basis=basis)


def test_combining_usage_keeps_the_weakest_basis():
    assert (_u("none") + _u("estimated", 1.0)).cost_basis == "estimated"
    assert (_u("actual", 1.0) + _u("actual", 2.0)).cost_basis == "actual"
    assert (_u("actual", 1.0) + _u("estimated", 2.0)).cost_basis == "estimated"
    assert (_u("estimated", 1.0) + _u("unavailable")).cost_basis == "unavailable"
    assert (_u("none") + _u("none")).cost_basis == "none"


def test_the_graph_state_merge_carries_the_basis():
    merged = merge_usage(
        {"total_tokens": 5, "estimated_cost_usd": 0.5, "cost_basis": "estimated"},
        {"total_tokens": 5, "estimated_cost_usd": 0.0, "cost_basis": "unavailable"},
    )
    assert merged["cost_basis"] == "unavailable"
    assert merge_usage({}, {"cost_basis": "actual"})["cost_basis"] == "actual"
    assert merge_usage(None, None)["cost_basis"] == "none"
