# Phase 5: system design evolution

> **Status of this phase:** in progress. P5-1 and P5-2 are implemented and checked locally; P5-3 and P5-4 are not started. Nothing is deployed, and there is no retriever or knowledge API yet.

---

## P5-1: knowledge articles and chunking

`rag/` is a new top-level package that knows nothing about tickets. `rag/chunking.py` loads the 15 articles in `sample_data/knowledge_base/` (YAML front-matter: title, category, tags, summary) and `chunk_article` splits each on headings, then into 900-character windows with a 150-character overlap. Every chunk's text is prefixed `"{title} - {heading}"`; `Chunk.body` holds the raw window so the size and overlap can be tested. Text before the first heading is filed under "Overview". Front-matter errors raise `ValueError` at load time. `pyyaml` is the one new dependency.

Boundary: `.claude/rules/rag.md` (`paths: rag/**`) and each module docstring state that `rag/` must not import ticket, repository or agent code. A test checks the imports.

---

## P5-2: vector store and fake embeddings

`rag/embeddings.py` defines the `Embeddings` protocol and `FakeEmbeddings`: lower-cased tokens are hashed (md5, so it is stable across processes) into 384 buckets by default, then L2-normalised, with no network and no numpy. `rag/vector_store.py` defines `Document` (id, text, vector, metadata with article_id, title, category, source, heading), the `VectorStoreService` protocol (`add_documents`, `search`, `delete`, `count`, `health`), `InMemoryVectorStore` (cosine similarity, equality filters, same id replaces) and `QdrantVectorStore`. The Qdrant class imports `qdrant_client` inside its methods, so offline runs never load it; the collection is created on first write and chunk ids map to stable UUID point ids. `get_vector_store(settings)` picks the class from `settings.vector_store` and caches it; `settings` is passed in, so `rag/` imports nothing from `app`. A test checks that nothing outside `rag/` names the concrete classes. Qdrant has only been exercised with a stubbed client; no server was run. `qdrant-client` is the one new dependency (it brings numpy).
