"""P5-2 (F5): fake embeddings, the in-memory store, and the VECTOR_STORE selector."""

import math
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from rag.embeddings import FakeEmbeddings
from rag.vector_store import (
    Document,
    InMemoryVectorStore,
    QdrantVectorStore,
    get_vector_store,
    reset_vector_store,
)

ROOT = Path(__file__).resolve().parents[2]


def _doc(emb: FakeEmbeddings, id_: str, text: str, category: str = "login_issue") -> Document:
    return Document(
        id=id_,
        text=text,
        metadata={
            "article_id": id_.split("#")[0],
            "title": "T",
            "category": category,
            "source": f"kb://{id_}",
            "heading": "H",
        },
        vector=emb.embed_query(text),
    )


def _dot(u: list[float], v: list[float]) -> float:
    return sum(x * y for x, y in zip(u, v, strict=True))


def test_embeddings_are_deterministic_384_dim_and_normalised():
    emb = FakeEmbeddings()
    a, b = emb.embed_query("reset my MFA device"), emb.embed_query("reset my MFA device")
    assert a == b
    assert len(a) == 384
    assert math.isclose(math.sqrt(sum(x * x for x in a)), 1.0, rel_tol=1e-9)
    assert emb.embed_documents(["x y", "z"]) == [emb.embed_query("x y"), emb.embed_query("z")]


def test_embeddings_honour_dimensions_and_empty_text():
    assert len(FakeEmbeddings(dimensions=64).embed_query("hello")) == 64
    assert FakeEmbeddings().embed_query("") == [0.0] * 384


def test_similar_text_scores_higher_than_unrelated():
    emb = FakeEmbeddings()
    q = emb.embed_query("locked out after MFA attempts")
    near = emb.embed_query("recover account locked by MFA attempts")
    far = emb.embed_query("invoice refund seats billing cycle")
    assert _dot(q, near) > _dot(q, far)


async def test_in_memory_add_search_delete_count():
    emb, store = FakeEmbeddings(), InMemoryVectorStore()
    await store.add_documents(
        [
            _doc(emb, "mfa#0", "MFA lockout recovery steps", "login_issue"),
            _doc(emb, "bill#0", "refund for unused seats billing", "billing"),
        ]
    )
    assert await store.count() == 2
    hits = await store.search(emb.embed_query("locked out MFA"), top_k=2)
    assert hits[0].document.id == "mfa#0"
    assert hits[0].score >= hits[1].score
    billing = await store.search(emb.embed_query("locked out MFA"), filters={"category": "billing"})
    assert [h.document.id for h in billing] == ["bill#0"]
    await store.delete(["mfa#0"])
    assert await store.count() == 1
    await store.add_documents([_doc(emb, "bill#0", "refund for unused seats billing", "billing")])
    assert await store.count() == 1  # same id replaces
    assert await store.health() is True


def test_selector_returns_memory_store_and_caches():
    mem = get_vector_store(SimpleNamespace(vector_store="memory"), fresh=True)
    assert isinstance(mem, InMemoryVectorStore)
    assert get_vector_store(SimpleNamespace(vector_store="memory")) is mem
    reset_vector_store()


def test_selector_qdrant_constructs_lazily_without_network(monkeypatch):
    calls = {}

    class FakeClient:
        def __init__(self, **kw):
            calls.update(kw)

    mod = ModuleType("qdrant_client")
    mod.QdrantClient = FakeClient
    monkeypatch.setitem(sys.modules, "qdrant_client", mod)
    settings = SimpleNamespace(
        vector_store="qdrant",
        qdrant_url="http://q:6333",
        qdrant_api_key=SimpleNamespace(get_secret_value=lambda: "k"),
        qdrant_collection="c",
        embedding_dimensions=384,
    )
    store = get_vector_store(settings, fresh=True)
    assert isinstance(store, QdrantVectorStore)
    assert store._client is None  # nothing imported or connected yet
    store._get_client()
    assert calls["url"] == "http://q:6333"
    reset_vector_store()


def test_qdrant_not_imported_at_module_level():
    source = (ROOT / "rag" / "vector_store.py").read_text(encoding="utf-8")
    top_level = [ln for ln in source.splitlines() if ln.startswith(("import ", "from "))]
    assert not any("qdrant_client" in ln for ln in top_level)


def test_nothing_outside_rag_imports_concrete_stores():
    pattern = re.compile(r"InMemoryVectorStore|QdrantVectorStore|rag\.vector_store")
    offenders = []
    for folder in ("backend", "agents", "memory", "integrations"):
        base = ROOT / folder
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if pattern.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path))
    assert offenders == []
