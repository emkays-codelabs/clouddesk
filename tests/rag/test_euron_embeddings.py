"""P9-10 (F5, F14): `EuronEmbeddings` over an OpenAI-compatible embeddings endpoint.

No test reaches Euron: `openai.OpenAI` is monkeypatched, and the suite's network guard would stop a
real call anyway.
"""

import pytest

from app.core.config import Settings
from app.services import knowledge_service
from rag.embeddings import (
    EURON_EMBEDDING_MODEL,
    EmbeddingError,
    EuronEmbeddings,
    FakeEmbeddings,
)

DIMS = 4


class Spy:
    """Stands in for `openai.OpenAI`: records each embeddings request, returns small vectors."""

    created: list[dict] = []
    requests: list[dict] = []
    dims = DIMS
    reverse = False
    drop_one = False
    fail = False

    def __init__(self, **kwargs):
        Spy.created.append(kwargs)
        self.embeddings = self

    def create(self, **kwargs):
        Spy.requests.append(kwargs)
        if Spy.fail:
            raise ConnectionError("down with key sk-secret-value")
        texts = kwargs["input"]
        items = [
            type("D", (), {"index": i, "embedding": [float(len(t))] + [0.5] * (Spy.dims - 1)})
            for i, t in enumerate(texts)
        ]
        if Spy.reverse:
            items.reverse()
        if Spy.drop_one:
            items = items[:-1]
        return type("R", (), {"data": items})


@pytest.fixture(autouse=True)
def spy(monkeypatch):
    Spy.created, Spy.requests = [], []
    Spy.dims, Spy.reverse, Spy.drop_one, Spy.fail = DIMS, False, False, False
    monkeypatch.setattr("openai.OpenAI", Spy)
    knowledge_service._euron.cache_clear()
    yield Spy
    knowledge_service._euron.cache_clear()


def _embeddings(**kw) -> EuronEmbeddings:
    kw.setdefault("api_key", "k")
    kw.setdefault("base_url", "http://localhost:1/v1")
    kw.setdefault("dimensions", DIMS)
    return EuronEmbeddings(**kw)


def test_it_satisfies_the_embeddings_protocol_and_uses_the_default_model():
    e = _embeddings()
    assert e.dimensions == DIMS
    assert e.embed_query("hello")[0] == 5.0
    assert Spy.requests[0]["model"] == EURON_EMBEDDING_MODEL == "euri-embedding"


def test_the_client_gets_the_key_and_base_url_and_no_sdk_retries():
    _embeddings(api_key="the-key", base_url="http://localhost:9/v1").embed_query("x")
    created = Spy.created[0]
    assert created["api_key"] == "the-key" and created["base_url"] == "http://localhost:9/v1"
    assert created["max_retries"] == 0


def test_documents_are_sent_in_batches_and_come_back_in_order():
    e = _embeddings(batch_size=2)
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]
    vectors = e.embed_documents(texts)
    assert [r["input"] for r in Spy.requests] == [["a", "bb"], ["ccc", "dddd"], ["eeeee"]]
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_vectors_are_placed_by_the_index_the_server_returns():
    Spy.reverse = True
    vectors = _embeddings().embed_documents(["a", "bb", "ccc"])
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0]


def test_an_empty_list_makes_no_request():
    assert _embeddings().embed_documents([]) == []
    assert Spy.requests == []


def test_the_dimension_is_read_from_the_first_response():
    e = _embeddings()
    assert e.detected_dimensions is None
    e.embed_query("x")
    assert e.detected_dimensions == DIMS


def test_a_dimension_mismatch_is_a_clear_error_naming_both_numbers_and_the_setting():
    Spy.dims = 7
    with pytest.raises(EmbeddingError) as info:
        _embeddings(dimensions=DIMS).embed_query("x")
    message = str(info.value)
    assert "7" in message and str(DIMS) in message and "EMBEDDING_DIMENSIONS" in message


def test_a_response_with_the_wrong_number_of_vectors_is_an_error():
    Spy.drop_one = True
    with pytest.raises(EmbeddingError, match="returned 1 vectors for 2"):
        _embeddings().embed_documents(["a", "b"])


def test_a_provider_failure_becomes_an_embedding_error_without_leaking_the_message():
    Spy.fail = True
    with pytest.raises(EmbeddingError) as info:
        _embeddings().embed_query("x")
    assert "ConnectionError" in str(info.value) and "sk-secret-value" not in str(info.value)


def test_empty_text_is_sent_as_a_space_because_the_endpoint_rejects_empty_input():
    _embeddings().embed_documents(["", "a"])
    assert Spy.requests[0]["input"] == [" ", "a"]


# ----------------------------------------------------------------------------- the selector


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def test_the_selector_builds_fake_by_default():
    e = knowledge_service.build_embeddings(_settings())
    assert isinstance(e, FakeEmbeddings) and e.dimensions == 384


def test_the_selector_builds_euron_with_the_documented_fallbacks():
    s = _settings(
        embedding_provider="euron",
        llm_api_key="llm-key",
        llm_base_url="http://localhost:2/v1",
        embedding_dimensions=DIMS,
    )
    e = knowledge_service.build_embeddings(s)
    assert isinstance(e, EuronEmbeddings)
    e.embed_query("x")
    assert Spy.created[0]["api_key"] == "llm-key"  # the key falls back to LLM_API_KEY
    assert Spy.created[0]["base_url"] == "http://localhost:2/v1"  # and so does the base URL
    assert Spy.requests[0]["model"] == "euri-embedding"


def test_the_embedding_base_url_and_model_win_over_the_fallbacks():
    s = _settings(
        embedding_provider="euron",
        llm_api_key="k",
        llm_base_url="http://localhost:2/v1",
        embedding_base_url="http://localhost:3/v1",
        embedding_model="custom-embed",
        embedding_dimensions=DIMS,
    )
    knowledge_service.build_embeddings(s).embed_query("x")
    assert Spy.created[0]["base_url"] == "http://localhost:3/v1"
    assert Spy.requests[0]["model"] == "custom-embed"


def test_with_no_base_url_set_the_euron_endpoint_is_used():
    s = _settings(embedding_provider="euron", llm_api_key="k", embedding_dimensions=DIMS)
    knowledge_service.build_embeddings(s).embed_query("x")
    assert Spy.created[0]["base_url"] == "https://api.euron.one/api/v1/euri"


def test_euron_without_any_key_is_refused_with_a_clear_error():
    with pytest.raises(EmbeddingError, match="LLM_API_KEY"):
        knowledge_service.build_embeddings(_settings(embedding_provider="euron"))


def test_an_unknown_provider_is_refused():
    with pytest.raises(EmbeddingError, match="EMBEDDING_PROVIDER"):
        knowledge_service.build_embeddings(_settings(embedding_provider="nope"))


def test_the_same_settings_give_the_same_instance_so_the_client_is_built_once():
    s = _settings(embedding_provider="euron", llm_api_key="k", embedding_dimensions=DIMS)
    assert knowledge_service.build_embeddings(s) is knowledge_service.build_embeddings(s)


def test_rag_imports_nothing_from_app():
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[2] / "rag"
    pattern = re.compile(r"^\s*(from|import)\s+app\b", re.M)
    assert [p.name for p in root.glob("*.py") if pattern.search(p.read_text("utf-8"))] == []
