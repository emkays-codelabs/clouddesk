"""P9-1: the LLM layer. The fake provider is valid and free, call_structured is the only door."""

import json
import re
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.llm import (
    EURON_BASE_URL,
    Completion,
    FakeProvider,
    LLMError,
    OpenAICompatibleProvider,
    call_structured,
    get_llm,
)
from app.core.readiness import check_readiness
from app.schemas.knowledge import Evidence
from app.schemas.workflow import (
    Classification,
    CustomerContext,
    Diagnosis,
    EscalationDecision,
    PreviousCase,
    ResolutionPlan,
    SeverityAssessment,
    WorkflowState,
)

ROOT = Path(__file__).resolve().parents[2]
ALL_MODELS = [
    Classification, SeverityAssessment, CustomerContext, Evidence, PreviousCase,
    Diagnosis, ResolutionPlan, EscalationDecision,
]  # fmt: skip


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


@pytest.mark.parametrize("model", ALL_MODELS)
async def test_fake_returns_valid_output_at_zero_cost(model):
    result = await call_structured(model, system="s", user="hello", llm=FakeProvider())
    assert isinstance(result.output, model)
    assert result.usage.estimated_cost_usd == 0.0
    assert result.usage.total_tokens > 0
    assert result.attempts == 1


async def test_fake_is_deterministic_and_sensible():
    user = "<untrusted_content>\nDark mode request, would be great\n</untrusted_content>"
    a = await call_structured(Classification, system="s", user=user, llm=FakeProvider())
    b = await call_structured(Classification, system="s", user=user, llm=FakeProvider())
    assert a.output == b.output
    assert a.output.category == "feature_request"
    sev = await call_structured(SeverityAssessment, system="s", user=user, llm=FakeProvider())
    assert sev.output.severity == "low"
    sec = "<untrusted_content>Suspicious logins, possible breach</untrusted_content>"
    c = await call_structured(Classification, system="s", user=sec, llm=FakeProvider())
    assert c.output.category == "security"


async def test_fake_honours_hints_for_known_fields_only():
    r = await call_structured(
        Classification, system="s", user="x", hints={"category": "billing", "bogus": 1},
        llm=FakeProvider(),
    )  # fmt: skip
    assert r.output.category == "billing"


class _Scripted:
    name, model = "scripted", "m"

    def __init__(self, replies):
        self.replies, self.calls, self.temps = list(replies), 0, []

    def estimate_cost(self, p, c):
        return 0.0

    async def complete(self, schema, messages, temperature, hints):
        self.calls += 1
        self.temps.append(temperature)
        return Completion(self.replies.pop(0), 10, 5)


async def test_invalid_output_is_repaired_then_succeeds():
    good = json.dumps({"category": "billing", "summary": "s"})
    llm = _Scripted(["not json", '{"category": "nope", "summary": "s"}', good])
    r = await call_structured(Classification, system="s", user="u", llm=llm)
    assert r.output.category == "billing"
    assert r.attempts == 3
    assert r.usage.total_tokens == 45


async def test_unrepairable_output_raises_llm_error_with_usage():
    llm = _Scripted(["bad"] * 5)
    with pytest.raises(LLMError) as info:
        await call_structured(Classification, system="s", user="u", llm=llm)
    assert llm.calls == 3  # first try plus two repairs
    assert info.value.usage.total_tokens == 45


async def test_provider_failure_is_llm_error_not_raw():
    class Boom(_Scripted):
        async def complete(self, *a):
            raise ConnectionError("down")

    with pytest.raises(LLMError):
        await call_structured(Classification, system="s", user="u", llm=Boom([]))


async def test_decision_temperature_is_capped():
    llm = _Scripted(['{"category": "other", "summary": "s"}'])
    await call_structured(Classification, system="s", user="u", temperature=0.9, llm=llm)
    assert llm.temps == [0.2]


def test_get_llm_defaults_to_fake_and_settings_override():
    assert isinstance(get_llm(_settings()), FakeProvider)
    p = get_llm(_settings(llm_provider="openai", llm_api_key="k", llm_model="gpt-x"))
    assert isinstance(p, OpenAICompatibleProvider) and p.model == "gpt-x"


def test_euron_uses_its_endpoint_and_model_without_network(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, **kw):
            seen.update(kw)

    monkeypatch.setattr("openai.AsyncOpenAI", FakeClient)
    get_llm.__globals__["_build_provider"].cache_clear()
    p = get_llm(_settings(llm_provider="euron", llm_api_key="test-key"))
    assert p.model == "euri-chat-smart"  # the router's default tier (P9-9)
    p._provider(p.model)  # providers are built on first use, so the client is built here
    assert seen["base_url"] == EURON_BASE_URL
    custom = get_llm(
        _settings(llm_provider="openai", llm_api_key="k", llm_base_url="http://localhost:1/v1")
    )
    assert seen["base_url"] == "http://localhost:1/v1" and custom.name == "openai"
    get_llm.__globals__["_build_provider"].cache_clear()


async def test_openai_compatible_complete_maps_usage(monkeypatch):
    class Msg:
        content = '{"category": "other", "summary": "s"}'

    class Resp:
        choices = [type("C", (), {"message": Msg})]
        usage = type("U", (), {"prompt_tokens": 7, "completion_tokens": 3})

    class Client:
        def __init__(self, **kw):
            self.chat = type("Ch", (), {"completions": self})

        async def create(self, **kw):
            return Resp

    monkeypatch.setattr("openai.AsyncOpenAI", Client)
    p = OpenAICompatibleProvider("openai", "k", None, "gpt-4o-mini")
    r = await call_structured(Classification, system="s", user="u", llm=p)
    assert r.usage.prompt_tokens == 7 and r.usage.estimated_cost_usd > 0


def test_real_provider_without_key_and_anthropic_raise_typed_errors():
    with pytest.raises(LLMError):
        get_llm(_settings(llm_provider="openai"))
    with pytest.raises(LLMError, match="not implemented"):
        get_llm(_settings(llm_provider="anthropic", llm_api_key="k"))


def test_readiness_fake_ok_others_need_a_key():
    assert check_readiness(_settings())["llm"].status == "ok"
    assert check_readiness(_settings(llm_provider="euron"))["llm"].status != "ok"
    assert check_readiness(_settings(llm_provider="euron", llm_api_key="k"))["llm"].status == "ok"


def test_no_model_sdk_imported_outside_core_llm():
    pattern = re.compile(r"^\s*(import|from)\s+(openai|langchain_openai|anthropic)\b", re.M)
    offenders = []
    for folder in ("backend", "agents", "rag", "memory", "integrations"):
        for path in (ROOT / folder).rglob("*.py"):
            if path.name == "llm.py" and path.parent.name == "core":
                continue
            if path.name == "embeddings.py" and path.parent.name == "rag":
                continue  # P9-10: the embeddings endpoint, checked in the test below
            if pattern.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_the_only_other_sdk_import_is_the_euron_embeddings_client_in_rag():
    text = (ROOT / "rag" / "embeddings.py").read_text(encoding="utf-8")
    imported = re.findall(r"^\s*(?:import|from)\s+(openai|langchain_openai|anthropic)", text, re.M)

    assert imported == ["openai"]  # one lazy import, inside EuronEmbeddings.__init__


def test_workflow_state_accepts_minimal_and_full_shapes():
    s = WorkflowState(workflow_id="w", ticket_id="t", status="running")
    assert s.token_usage.estimated_cost_usd == 0.0 and s.retrieved_docs == []
    full = WorkflowState(
        workflow_id="w", ticket_id="t", status="completed",
        classification={"category": "billing", "summary": "x"},
        risk={"level": "high", "reasons": ["refund"]},
        extra_key=1,
    )  # fmt: skip
    assert full.classification.category == "billing"
