"""The LLM layer (F14): `get_llm()` picks a provider, `call_structured()` is the one way in.

Does: offer one `LLMProvider` interface with three implementations: `fake` (offline, deterministic,
cost 0.0, the default), and an OpenAI-compatible client for `openai` and for Euron's endpoint
(`euron`). `call_structured` validates the reply against a Pydantic model, repairs an invalid reply
at most twice, measures usage and latency, and raises only a typed `LLMError` (which still carries
the usage spent). One model, no tiers, no gateway (ADR-0010, D4 not decided).
Must NOT: be bypassed. A static test fails when `openai` or `langchain_openai` is imported outside
this file. Must not import `agents/` (core layer); callers pass rule results as `hints`. Must not
log or return the API key, the prompt, or the base URL's credentials.
"""

import json
import logging
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.schemas.workflow import TokenUsage

logger = logging.getLogger(__name__)

MAX_REPAIRS = 2
DECISION_TEMPERATURE_CAP = 0.2
EURON_BASE_URL = "https://api.euron.one/api/v1/euri"
EURON_DEFAULT_MODEL = "euri-reasoning"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT_SECONDS = 60.0

# USD per million tokens (input, output). Estimates only; a model not listed is costed at 0.0.
PRICE_PER_MILLION: dict[str, tuple[float, float]] = {"gpt-4o-mini": (0.15, 0.60)}


class LLMError(Exception):
    """The model could not produce a valid answer. `usage` is what was spent trying."""

    def __init__(self, message: str, usage: TokenUsage | None = None, latency_ms: int = 0):
        super().__init__(message)
        self.usage = usage or TokenUsage()
        self.latency_ms = latency_ms


@dataclass
class Completion:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class StructuredResult[T]:
    output: T
    usage: TokenUsage
    latency_ms: int
    attempts: int = 1
    provider: str = ""
    model: str = ""
    errors: list[str] = field(default_factory=list)


class LLMProvider(Protocol):
    name: str
    model: str

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float: ...

    async def complete(
        self,
        schema: type[BaseModel],
        messages: Sequence[dict[str, str]],
        temperature: float,
        hints: dict[str, Any] | None,
    ) -> Completion: ...


# ----------------------------------------------------------------------------- fake provider

_UNTRUSTED = re.compile(r"<untrusted_content>(.*?)</untrusted_content>", re.DOTALL | re.IGNORECASE)

# Ordered: the first category with the most keyword hits wins; ties go to the earlier entry.
_FAKE_CATEGORIES: tuple[tuple[str, str], ...] = (
    (
        "security",
        r"breach|compromis|hacked|suspicious|unauthori[sz]ed access|"
        r"ignore\s+(all\s+)?(previous\s+)?instructions|export all customer",
    ),
    ("billing", r"refund|invoice|billed|billing|charge|payment|dispute|seats?\b|subscription"),
    ("api_failure", r"\bapi\b|429|rate.?limit|webhook|token expired|5\d\d error|sync"),
    ("storage_quota", r"quota|storage|upload|disk|out of space"),
    ("login_issue", r"\bsso\b|log ?in|sign ?in|password|mfa|locked out|two.factor"),
    ("workspace_permissions", r"permission|share|sharing|access denied|role|invite|external"),
    ("integration", r"integration|slack|zapier|jira|connector|plugin"),
    ("feature_request", r"dark mode|feature request|would be great|please add|wish|suggestion"),
    ("account", r"delete.*(account|workspace)|erase|close.*account|profile|rename|transfer"),
)
_FAKE_HIGH = re.compile(
    r"whole team|everyone|all users|entire (team|company)|outage|production|breach|suspicious|"
    r"disappear|vanished|unauthori[sz]ed|dispute|delete|erase|can'?t (log|sign)"
)
_FAKE_LOW = re.compile(r"dark mode|feature request|would be great|please add|suggestion")
_FAKE_TEAMS = {
    "security": "Security team",
    "billing": "Billing disputes team",
    "account": "Privacy team",
}


def _evidence_text(messages: Sequence[dict[str, str]]) -> str:
    """The ticket text the heuristics read: the untrusted blocks, else the last user message."""
    users = [m["content"] for m in messages if m["role"] == "user"]
    body = users[-1] if users else ""
    blocks = _UNTRUSTED.findall(body)
    return " ".join(blocks) if blocks else body


def _fake_category(text: str) -> str:
    best, best_hits = "other", 0
    for category, pattern in _FAKE_CATEGORIES:
        hits = len(re.findall(pattern, text, re.IGNORECASE))
        if hits > best_hits:
            best, best_hits = category, hits
    return best


def _first_sentence(text: str, limit: int = 140) -> str:
    flat = " ".join(text.split())
    return (re.split(r"(?<=[.!?])\s", flat, maxsplit=1)[0] or flat)[:limit]


def _fake_severity(text: str) -> str:
    if _FAKE_LOW.search(text):
        return "low"
    return "high" if _FAKE_HIGH.search(text) else "medium"


def _fake_values(name: str, text: str) -> dict[str, Any]:
    """Deterministic, schema-valid values for the five models a model is asked for."""
    category = _fake_category(text)
    sentence = _first_sentence(text) or "No ticket text supplied."
    if name == "Classification":
        return {
            "category": category,
            "intent": category.replace("_", " "),
            "summary": sentence,
            "confidence": 0.9 if category != "other" else 0.4,
        }
    if name == "SeverityAssessment":
        severity = _fake_severity(text)
        return {
            "severity": severity,
            "reason": f"Judged {severity} from the wording of the ticket.",
            "confidence": 0.8,
        }
    if name == "Diagnosis":
        label = category.replace("_", " ")
        return {
            "problem": sentence,
            "probable_causes": [f"A common {label} cause matches the report."],
            "troubleshooting_steps": [
                "Confirm the details in the ticket with the customer.",
                f"Follow the documented {label} procedure.",
                "Check the service status page for an active incident.",
            ],
            "confidence": 0.8,
        }
    if name == "ResolutionPlan":
        return {
            "summary": f"Resolve: {sentence}",
            "customer_response": (
                "Thanks for contacting CloudDesk. We have reviewed your request and are working "
                "through the documented steps. We will confirm once it is resolved."
            ),
            "internal_notes": f"Fake provider plan for a {category} ticket.",
            "actions": [],
        }
    if name == "EscalationDecision":
        escalate = _fake_severity(text) == "high" and category in _FAKE_TEAMS
        return {
            "escalation_required": escalate,
            "reason": "The ticket needs a specialist team." if escalate else "",
            "assigned_team": _FAKE_TEAMS.get(category, "") if escalate else "",
            "priority": "high" if escalate else "medium",
            "confidence": 0.8,
        }
    return {}


def _default_for(node: dict[str, Any], defs: dict[str, Any]) -> Any:
    """The smallest valid value for a JSON-schema node, so any output model can be answered."""
    if "$ref" in node:
        return _default_for(defs[node["$ref"].rsplit("/", 1)[-1]], defs)
    if "default" in node:
        return node["default"]
    if "enum" in node:
        return node["enum"][0]
    if "anyOf" in node:
        options = [o for o in node["anyOf"] if o.get("type") != "null"]
        return _default_for(options[0], defs) if options else None
    if "allOf" in node:
        return _default_for(node["allOf"][0], defs)
    kind = node.get("type")
    if kind == "string":
        return "1970-01-01T00:00:00Z" if node.get("format") == "date-time" else ""
    if kind == "integer":
        return int(node.get("minimum", 0))
    if kind == "number":
        return float(node.get("minimum", 0))
    if kind == "boolean":
        return False
    if kind == "array":
        return []
    if kind == "object" or "properties" in node:
        required = node.get("required", [])
        props = node.get("properties", {})
        return {k: _default_for(props[k], defs) for k in required if k in props}
    return None


class FakeProvider:
    """Offline and deterministic: same input, same output, no network, cost 0.0 (F14)."""

    name = "fake"
    model = "fake"

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    async def complete(
        self,
        schema: type[BaseModel],
        messages: Sequence[dict[str, str]],
        temperature: float,
        hints: dict[str, Any] | None,
    ) -> Completion:
        json_schema = schema.model_json_schema()
        defs = json_schema.get("$defs", {})
        value = _default_for(json_schema, defs)
        if not isinstance(value, dict):
            value = {}
        value.update(_fake_values(schema.__name__, _evidence_text(messages)))
        properties = json_schema.get("properties", {})
        value.update({k: v for k, v in (hints or {}).items() if k in properties})
        text = json.dumps(value, default=str)
        prompt = sum(len(m["content"]) for m in messages) // 4
        return Completion(text=text, prompt_tokens=prompt, completion_tokens=len(text) // 4)


# ----------------------------------------------------------------------------- openai-compatible


class OpenAICompatibleProvider:
    """Chat completions against any OpenAI-compatible endpoint (OpenAI itself, or Euron's euri)."""

    def __init__(self, name: str, api_key: str, base_url: str | None, model: str):
        from openai import AsyncOpenAI  # the one place the SDK is imported

        self.name = name
        self.model = model
        # max_retries=0: retries are call_structured's job, so usage and latency stay honest.
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        rate_in, rate_out = PRICE_PER_MILLION.get(self.model, (0.0, 0.0))
        return (prompt_tokens * rate_in + completion_tokens * rate_out) / 1_000_000

    async def complete(
        self,
        schema: type[BaseModel],
        messages: Sequence[dict[str, str]],
        temperature: float,
        hints: dict[str, Any] | None,
    ) -> Completion:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=list(messages),  # type: ignore[arg-type]
            temperature=temperature,
        )
        usage = response.usage
        return Completion(
            text=response.choices[0].message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )


@lru_cache(maxsize=8)
def _build_provider(provider: str, api_key: str, model: str, base_url: str) -> LLMProvider:
    if provider == "fake":
        return FakeProvider()
    if provider == "openai":
        return OpenAICompatibleProvider(
            "openai", api_key, base_url or None, model or OPENAI_DEFAULT_MODEL
        )
    if provider == "euron":
        return OpenAICompatibleProvider(
            "euron", api_key, base_url or EURON_BASE_URL, model or EURON_DEFAULT_MODEL
        )
    if provider == "anthropic":
        raise LLMError("The anthropic provider is not implemented; use fake, openai or euron.")
    raise LLMError(f"Unknown LLM_PROVIDER {provider!r}; use fake, openai or euron.")


def get_llm(settings: Settings | None = None) -> LLMProvider:
    """The provider for `settings.llm_provider`. Building one makes no network call."""
    s = settings or get_settings()
    provider = s.llm_provider.strip().lower()
    key = s.llm_api_key.get_secret_value()
    if provider in ("openai", "euron") and not key:
        raise LLMError(f"LLM_API_KEY is not set for the {provider} provider.")
    return _build_provider(provider, key, s.llm_model, s.llm_base_url)


# ----------------------------------------------------------------------------- call_structured


def _extract_json(text: str) -> Any:
    """Parse a reply that may carry think-tags, a code fence or prose around one JSON object."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object in the reply")
    return json.loads(cleaned[start : end + 1])


def _system_with_schema(system: str, schema: type[BaseModel]) -> str:
    spec = json.dumps(schema.model_json_schema())
    return f"{system}\n\nReply with one JSON object only, matching this JSON Schema:\n{spec}"


async def call_structured[T: BaseModel](
    schema: type[T],
    *,
    system: str,
    user: str,
    temperature: float = 0.0,
    hints: dict[str, Any] | None = None,
    llm: LLMProvider | None = None,
) -> StructuredResult[T]:
    """Ask the model for a `schema` object. The only sanctioned way to call a model.

    Decisions run at temperature <= 0.2, so the value is capped. An invalid reply is sent back with
    the validation errors up to MAX_REPAIRS times. `hints` are rule results the fake provider
    honours (a real model ignores them). Raises LLMError only, carrying the usage spent.
    """
    started = time.perf_counter()
    usage = TokenUsage()
    temperature = min(max(temperature, 0.0), DECISION_TEMPERATURE_CAP)
    provider = llm or get_llm()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _system_with_schema(system, schema)},
        {"role": "user", "content": user},
    ]
    problems: list[str] = []

    def elapsed() -> int:
        return int((time.perf_counter() - started) * 1000)

    for attempt in range(1, MAX_REPAIRS + 2):
        try:
            completion = await provider.complete(schema, messages, temperature, hints)
        except Exception as exc:  # any provider failure, mapped to the one typed error
            logger.warning("llm provider call failed: %s", type(exc).__name__)
            raise LLMError(
                f"{provider.name} call failed: {type(exc).__name__}", usage, elapsed()
            ) from exc
        cost = provider.estimate_cost(completion.prompt_tokens, completion.completion_tokens)
        usage = usage + TokenUsage(
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            total_tokens=completion.prompt_tokens + completion.completion_tokens,
            estimated_cost_usd=cost,
        )
        try:
            output = schema.model_validate(_extract_json(completion.text))
        except (ValueError, ValidationError) as exc:
            problem = str(exc)[:500]
            problems.append(problem)
            if attempt > MAX_REPAIRS:
                break
            messages = [
                *messages,
                {"role": "assistant", "content": completion.text},
                {
                    "role": "user",
                    "content": f"That reply was invalid: {problem}\nReturn only corrected JSON.",
                },
            ]
            continue
        latency = elapsed()
        logger.info(
            "llm call ok",
            extra={"provider": provider.name, "schema": schema.__name__, "attempts": attempt},
        )
        return StructuredResult(
            output=output,
            usage=usage,
            latency_ms=latency,
            attempts=attempt,
            provider=provider.name,
            model=provider.model,
            errors=problems,
        )
    raise LLMError(
        f"{schema.__name__}: no valid output after {MAX_REPAIRS} repairs ({problems[-1][:200]})",
        usage,
        elapsed(),
    )
