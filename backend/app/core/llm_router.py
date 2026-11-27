"""The Euron router (P9-9, F14): three model tiers, a fallback chain and a circuit breaker.

Does: map a tier (`fast`, `smart`, `reasoning`) to a model, call that model, and on a provider
failure fall back along `reasoning` -> `smart` -> `fast` (a lower tier never escalates upward).
Each model has a breaker: 5 failures within 60 s open it for 60 s, and an open model is skipped
without being called. The answer reports the tier that was asked for and the model that
served it, so every call can be recorded. It lives in process: ADR-0010 accepted a router,
not a gateway service.
Must NOT: import the SDK or `llm.py` (it only needs a provider factory and the shape of a
`Completion`), import `agents/`, or retry an invalid reply (that is `call_structured`'s repair loop,
on the same model). The fake provider never goes through here, so it ignores tiers.
"""

import dataclasses
import time
from collections import defaultdict, deque
from collections.abc import Callable, Sequence
from typing import Any, Literal, get_args

from pydantic import BaseModel

Tier = Literal["fast", "smart", "reasoning"]
TIERS: tuple[str, ...] = get_args(Tier)
DEFAULT_TIER: Tier = "smart"
TIER_DEFAULTS: dict[str, str] = {
    "fast": "euri-chat-fast",
    "smart": "euri-chat-smart",
    "reasoning": "euri-reasoning",
}
# The chain tried for a tier, in order. A tier only ever falls to the cheaper ones below it.
FALLBACK_CHAIN: dict[str, tuple[str, ...]] = {
    "reasoning": ("reasoning", "smart", "fast"),
    "smart": ("smart", "fast"),
    "fast": ("fast",),
}
FAILURE_THRESHOLD = 5
FAILURE_WINDOW_SECONDS = 60.0
OPEN_SECONDS = 60.0


class RouterError(Exception):
    """No model in the chain could answer: every one failed or had its breaker open."""


def tier_models(llm_model: str, fast: str, smart: str, reasoning: str) -> dict[str, str]:
    """The model per tier: the tier's own setting, else `LLM_MODEL`, else the tier default."""
    chosen = {"fast": fast, "smart": smart, "reasoning": reasoning}
    return {tier: chosen[tier] or llm_model or TIER_DEFAULTS[tier] for tier in TIERS}


class CircuitBreaker:
    """Per-model breaker: `threshold` failures inside `window` seconds open it for `open_for`."""

    def __init__(
        self,
        *,
        threshold: int = FAILURE_THRESHOLD,
        window: float = FAILURE_WINDOW_SECONDS,
        open_for: float = OPEN_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._threshold, self._window, self._open_for, self._clock = (
            threshold,
            window,
            open_for,
            clock,
        )
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._open_until: dict[str, float] = {}

    def is_open(self, model: str) -> bool:
        until = self._open_until.get(model)
        if until is None:
            return False
        if self._clock() >= until:
            del self._open_until[model]  # half-open: the next call is allowed through
            self._failures[model].clear()
            return False
        return True

    def record_failure(self, model: str) -> None:
        now = self._clock()
        failures = self._failures[model]
        failures.append(now)
        while failures and now - failures[0] > self._window:
            failures.popleft()
        if len(failures) >= self._threshold:
            self._open_until[model] = now + self._open_for

    def record_success(self, model: str) -> None:
        self._failures[model].clear()
        self._open_until.pop(model, None)


class LLMRouter:
    """An `LLMProvider` that serves a tier from the model chain. Tiered: it takes a `tier`."""

    supports_tiers = True

    def __init__(
        self,
        models: dict[str, str],
        make_provider: Callable[[str], Any],
        *,
        name: str = "euron",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self.models = dict(models)
        self.model = self.models[DEFAULT_TIER]
        self._make_provider = make_provider
        self._providers: dict[str, Any] = {}
        self._breaker = CircuitBreaker(clock=clock)

    def is_open(self, model: str) -> bool:
        return self._breaker.is_open(model)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        return None  # no Euron price is verified; set LLM_PRICING to get an estimate

    def _provider(self, model: str) -> Any:
        if model not in self._providers:
            self._providers[model] = self._make_provider(model)
        return self._providers[model]

    def _chain(self, tier: str) -> list[tuple[str, str]]:
        """(tier, model) pairs to try, a model that serves two tiers only once."""
        seen: set[str] = set()
        chain = []
        for t in FALLBACK_CHAIN[tier]:
            model = self.models[t]
            if model not in seen:
                seen.add(model)
                chain.append((t, model))
        return chain

    async def complete(
        self,
        schema: type[BaseModel],
        messages: Sequence[dict[str, str]],
        temperature: float,
        hints: dict[str, Any] | None,
        tier: str = DEFAULT_TIER,
    ) -> Any:
        if tier not in FALLBACK_CHAIN:
            raise ValueError(f"unknown tier {tier!r}; use one of {', '.join(TIERS)}")
        tried: list[str] = []
        for served_tier, model in self._chain(tier):
            if self._breaker.is_open(model):
                tried.append(f"{model} (breaker open)")
                continue
            try:
                completion = await self._provider(model).complete(
                    schema, messages, temperature, hints
                )
            except Exception as exc:  # any provider failure counts against that model only
                self._breaker.record_failure(model)
                tried.append(f"{model} ({type(exc).__name__})")
                continue
            self._breaker.record_success(model)
            return dataclasses.replace(completion, model=model, tier=served_tier)
        raise RouterError(f"{tier}: every model unavailable: {', '.join(tried)}")
