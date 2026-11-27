"""P9-9 (F14): the in-process Euron router: tiers, fallback chain, circuit breaker, recording.

No test here reaches Euron. The router is driven with scripted providers, or with a monkeypatched
`openai.AsyncOpenAI`, and the suite's network guard would stop a real call anyway.
"""

import logging

import pytest

from app.core.config import Settings
from app.core.llm import (
    Completion,
    FakeProvider,
    LLMError,
    call_structured,
    get_llm,
)
from app.core.llm_router import (
    TIER_DEFAULTS,
    CircuitBreaker,
    LLMRouter,
    tier_models,
)
from app.schemas.workflow import Classification

GOOD = '{"category": "other", "summary": "s"}'
MODELS = {"fast": "m-fast", "smart": "m-smart", "reasoning": "m-reasoning"}


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Scripted:
    """A provider for one model: answers, or raises while `down` is true."""

    def __init__(self, model: str, calls: list[str], down: set[str]) -> None:
        self.name, self.model, self._calls, self._down = "scripted", model, calls, down

    def estimate_cost(self, p, c):
        return 0.0

    async def complete(self, schema, messages, temperature, hints):
        self._calls.append(self.model)
        if self.model in self._down:
            raise ConnectionError("down")
        return Completion(GOOD, 10, 5)


def _router(down=(), clock=None, models=None):
    calls: list[str] = []
    down_set = set(down)
    router = LLMRouter(
        models or MODELS,
        lambda model: Scripted(model, calls, down_set),
        clock=clock or Clock(),
    )
    return router, calls, down_set


# ----------------------------------------------------------------------------- model resolution


def test_each_tier_has_its_documented_default():
    assert TIER_DEFAULTS == {
        "fast": "euri-chat-fast",
        "smart": "euri-chat-smart",
        "reasoning": "euri-reasoning",
    }
    assert tier_models("", "", "", "") == TIER_DEFAULTS


def test_a_tier_model_falls_back_to_llm_model_then_to_the_default():
    assert tier_models("one-model", "", "", "") == dict.fromkeys(TIER_DEFAULTS, "one-model")
    got = tier_models("one-model", "f", "", "r")
    assert got == {"fast": "f", "smart": "one-model", "reasoning": "r"}


def test_settings_carry_the_three_tier_models():
    s = _settings(llm_model_fast="a", llm_model_smart="b", llm_model_reasoning="c")
    assert (s.llm_model_fast, s.llm_model_smart, s.llm_model_reasoning) == ("a", "b", "c")
    assert _settings().llm_model_fast == ""


# ----------------------------------------------------------------------------- routing


async def test_each_tier_is_served_by_its_own_model():
    router, calls, _ = _router()
    for tier in ("fast", "smart", "reasoning"):
        await call_structured(Classification, system="s", user="u", tier=tier, llm=router)
    assert calls == ["m-fast", "m-smart", "m-reasoning"]


async def test_the_default_tier_is_smart():
    router, calls, _ = _router()
    await call_structured(Classification, system="s", user="u", llm=router)
    assert calls == ["m-smart"]


async def test_reasoning_falls_back_to_smart_then_to_fast():
    router, calls, down = _router(down={"m-reasoning"})
    r = await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls == ["m-reasoning", "m-smart"]
    assert (r.tier, r.served_tier, r.model) == ("reasoning", "smart", "m-smart")

    calls.clear()
    down.add("m-smart")
    r = await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls == ["m-reasoning", "m-smart", "m-fast"]
    assert (r.served_tier, r.model) == ("fast", "m-fast")


async def test_smart_falls_back_to_fast_and_fast_has_nothing_below_it():
    router, calls, down = _router(down={"m-smart"})
    r = await call_structured(Classification, system="s", user="u", tier="smart", llm=router)
    assert calls == ["m-smart", "m-fast"] and r.served_tier == "fast"

    calls.clear()
    down.add("m-fast")
    with pytest.raises(LLMError):
        await call_structured(Classification, system="s", user="u", tier="fast", llm=router)
    assert calls == ["m-fast"]


async def test_a_lower_tier_never_escalates_upward():
    router, calls, _ = _router(down={"m-fast"})
    with pytest.raises(LLMError):
        await call_structured(Classification, system="s", user="u", tier="fast", llm=router)
    assert "m-smart" not in calls and "m-reasoning" not in calls


async def test_one_model_serving_two_tiers_is_not_called_twice_in_a_chain():
    same = {"fast": "x", "smart": "x", "reasoning": "x"}
    router, calls, _ = _router(down={"x"}, models=same)
    with pytest.raises(LLMError):
        await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls == ["x"]


async def test_an_invalid_reply_is_repaired_on_the_same_model_not_a_fallback():
    calls: list[str] = []
    replies = ["not json", GOOD]

    class Flaky(Scripted):
        async def complete(self, schema, messages, temperature, hints):
            self._calls.append(self.model)
            return Completion(replies.pop(0), 1, 1)

    router = LLMRouter(MODELS, lambda m: Flaky(m, calls, set()), clock=Clock())
    r = await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls == ["m-reasoning", "m-reasoning"] and r.attempts == 2


async def test_an_unknown_tier_is_refused_before_any_call():
    router, calls, _ = _router()
    with pytest.raises(ValueError, match="tier"):
        await call_structured(Classification, system="s", user="u", tier="huge", llm=router)  # type: ignore[arg-type]
    assert calls == []


# ----------------------------------------------------------------------------- circuit breaker


async def test_five_failures_in_a_minute_open_the_breaker_and_the_model_is_skipped():
    clock = Clock()
    router, calls, _ = _router(down={"m-reasoning"}, clock=clock)
    for _ in range(5):
        await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
        clock.now += 1
    assert calls.count("m-reasoning") == 5

    calls.clear()
    r = await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls == ["m-smart"]  # m-reasoning was not called at all
    assert r.served_tier == "smart"


async def test_four_failures_do_not_open_it():
    clock = Clock()
    router, calls, _ = _router(down={"m-reasoning"}, clock=clock)
    for _ in range(4):
        await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    calls.clear()
    await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls[0] == "m-reasoning"


async def test_the_breaker_closes_again_after_sixty_seconds():
    clock = Clock()
    router, calls, down = _router(down={"m-reasoning"}, clock=clock)
    for _ in range(5):
        await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    clock.now += 59
    calls.clear()
    await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert "m-reasoning" not in calls

    clock.now += 2  # 61 s since it opened
    down.clear()
    calls.clear()
    r = await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert calls == ["m-reasoning"] and r.served_tier == "reasoning"


async def test_failures_older_than_a_minute_do_not_count():
    clock = Clock()
    router, _, _ = _router(down={"m-reasoning"}, clock=clock)
    for _ in range(4):
        await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    clock.now += 61
    await call_structured(Classification, system="s", user="u", tier="reasoning", llm=router)
    assert not router.is_open("m-reasoning")


async def test_when_every_model_is_open_the_call_fails_with_llm_error_and_calls_nothing():
    clock = Clock()
    router, calls, _ = _router(down=set(MODELS.values()), clock=clock)
    for _ in range(5):
        with pytest.raises(LLMError):
            await call_structured(Classification, system="s", user="u", tier="fast", llm=router)
    calls.clear()
    with pytest.raises(LLMError, match="unavailable"):
        await call_structured(Classification, system="s", user="u", tier="fast", llm=router)
    assert calls == []


def test_breaker_unit_threshold_and_window():
    clock = Clock()
    breaker = CircuitBreaker(clock=clock)
    for _ in range(4):
        breaker.record_failure("m")
    assert not breaker.is_open("m")
    breaker.record_failure("m")
    assert breaker.is_open("m") and not breaker.is_open("other")
    breaker.record_success("m")
    assert not breaker.is_open("m")


# ----------------------------------------------------------------------------- recording


async def test_the_tier_model_and_usage_of_each_call_are_recorded(caplog):
    router, _, _ = _router(down={"m-reasoning"})
    with caplog.at_level(logging.INFO, logger="app.core.llm"):
        r = await call_structured(
            Classification, system="s", user="u", tier="reasoning", llm=router
        )
    assert (r.tier, r.served_tier, r.model, r.provider) == (
        "reasoning", "smart", "m-smart", "euron",
    )  # fmt: skip
    assert r.usage.prompt_tokens == 10 and r.usage.completion_tokens == 5
    record = next(x for x in caplog.records if x.getMessage() == "llm call ok")
    assert record.tier == "reasoning" and record.served_tier == "smart"
    assert record.model == "m-smart" and record.total_tokens == 15


# ----------------------------------------------------------------------------- get_llm and fake


def test_get_llm_builds_a_router_for_euron_with_the_tier_models(monkeypatch):
    seen = []

    class Client:
        def __init__(self, **kw):
            seen.append(kw)

    monkeypatch.setattr("openai.AsyncOpenAI", Client)
    get_llm.__globals__["_build_provider"].cache_clear()
    router = get_llm(_settings(llm_provider="euron", llm_api_key="k", llm_model_fast="f1"))
    assert isinstance(router, LLMRouter) and router.name == "euron"
    assert router.models == {
        "fast": "f1",
        "smart": "euri-chat-smart",
        "reasoning": "euri-reasoning",
    }
    assert router.model == "euri-chat-smart"
    assert seen == []  # providers are built lazily, on first use: building the router is free
    get_llm.__globals__["_build_provider"].cache_clear()


async def test_the_router_sends_each_tier_to_its_model_through_the_client(monkeypatch):
    used: list[str] = []

    class Msg:
        content = GOOD

    class Resp:
        choices = [type("C", (), {"message": Msg})]
        usage = type("U", (), {"prompt_tokens": 7, "completion_tokens": 3})

    class Client:
        def __init__(self, **kw):
            self.chat = type("Ch", (), {"completions": self})

        async def create(self, **kw):
            used.append(kw["model"])
            return Resp

    monkeypatch.setattr("openai.AsyncOpenAI", Client)
    get_llm.__globals__["_build_provider"].cache_clear()
    router = get_llm(_settings(llm_provider="euron", llm_api_key="k"))
    for tier in ("fast", "smart", "reasoning"):
        await call_structured(Classification, system="s", user="u", tier=tier, llm=router)
    assert used == ["euri-chat-fast", "euri-chat-smart", "euri-reasoning"]
    get_llm.__globals__["_build_provider"].cache_clear()


async def test_the_fake_provider_ignores_tiers():
    outputs = []
    for tier in ("fast", "smart", "reasoning"):
        r = await call_structured(
            Classification, system="s", user="dark mode please", tier=tier, llm=FakeProvider()
        )
        outputs.append(r.output)
        assert r.usage.estimated_cost_usd == 0.0 and r.provider == "fake"
    assert outputs[0] == outputs[1] == outputs[2]
