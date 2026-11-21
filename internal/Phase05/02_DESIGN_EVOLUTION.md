# Phase 5: system design evolution

> **Status of this phase:** in progress. P5-1 to P5-4 are implemented and checked locally. Nothing is deployed, and Qdrant and a real Redis have not been run.

---

## P5-1: knowledge articles and chunking

`rag/` is a new top-level package that knows nothing about tickets. `rag/chunking.py` loads the 15 articles in `sample_data/knowledge_base/` (YAML front-matter: title, category, tags, summary) and `chunk_article` splits each on headings, then into 900-character windows with a 150-character overlap. Every chunk's text is prefixed `"{title} - {heading}"`; `Chunk.body` holds the raw window so the size and overlap can be tested. Text before the first heading is filed under "Overview". Front-matter errors raise `ValueError` at load time. `pyyaml` is the one new dependency.

Boundary: `.claude/rules/rag.md` (`paths: rag/**`) and each module docstring state that `rag/` must not import ticket, repository or agent code. A test checks the imports.

---

## P5-2: vector store and fake embeddings

`rag/embeddings.py` defines the `Embeddings` protocol and `FakeEmbeddings`: lower-cased tokens are hashed (md5, so it is stable across processes) into 384 buckets by default, then L2-normalised, with no network and no numpy. `rag/vector_store.py` defines `Document` (id, text, vector, metadata with article_id, title, category, source, heading), the `VectorStoreService` protocol (`add_documents`, `search`, `delete`, `count`, `health`), `InMemoryVectorStore` (cosine similarity, equality filters, same id replaces) and `QdrantVectorStore`. The Qdrant class imports `qdrant_client` inside its methods, so offline runs never load it; the collection is created on first write and chunk ids map to stable UUID point ids. `get_vector_store(settings)` picks the class from `settings.vector_store` and caches it; `settings` is passed in, so `rag/` imports nothing from `app`. A test checks that nothing outside `rag/` names the concrete classes. Qdrant has only been exercised with a stubbed client; no server was run. `qdrant-client` is the one new dependency (it brings numpy).

---

## P5-3: hybrid retriever

`rag/retriever.py` adds `HybridRetriever(store, embeddings, documents, ...)`. A query is rewritten deterministically into up to three sub-queries (original, stop-word-stripped, longest-words variant; an optional `rewriter` hook can add one). Each sub-query gets a semantic ranking from the vector store and a BM25 ranking (`rank_bm25`); the rankings are fused with reciprocal rank fusion (k=60), reranked by title overlap and a category bonus, optionally reordered by an injected `llm_rerank` hook, and reduced to one hit per article. Modes are `hybrid` (default), `semantic` and `keyword`; `category` is a hard filter unless `strict_category=False`, where it only boosts.

A deterministic sufficiency check (top score at least 0.3 and at least half the query terms found in the top three hits) may run ONE extra ranking pass on the uncovered terms, then stops. Results are cached 300 s under `rag:{mode}:{category}:{top_k}:{query}` through an injected object with `get` and `set(ttl)`; `backend/app/services/retrieval_cache.py` adapts the Redis client, so `rag/` imports nothing from `app`. `chunk_filter` is the hook where P7-2 will drop injected chunks; the default passes everything. Evidence is `{id, title, source, snippet, score, url, article_id}`. hit-rate@3 over 11 queries taken from the demo tickets is 1.0 with fake embeddings. The cache was only exercised with fakeredis; `documents_from_chunks` is the bridge P5-4 ingest will reuse.

---

## P5-4: ingest command and knowledge API

`rag/ingest.py` adds `ingest(store, embeddings, directory, recreate=False)`, returning article and chunk counts (15 and 75 on the demo articles). It is idempotent because chunk ids are stable and the store replaces a document with the same id; `recreate=True` calls the new `VectorStoreService.clear()` (in-memory: empty the dict; Qdrant: delete the collection, recreated on the next write), so stale chunks go too. `rag.ingest` re-exports `get_vector_store` so code outside `rag/` still never names `rag.vector_store`.

`backend/app/services/knowledge_service.py` keeps the in-process article and chunk state, serves `GET /knowledge/articles` (search, category), `GET /knowledge/articles/{id}` (ids are file slugs), `POST /knowledge/search` (retriever plus the Redis cache adapter) and admin-only `POST /knowledge/reindex`, whose `indexed` is the chunk count. The lifespan indexes the knowledge base at startup only when `VECTOR_STORE=memory`; a failure is logged and never stops startup. `make ingest` runs `python -m app.services.knowledge_service` (the CLI lives in `app` because it needs settings, which `rag/` may not import); it fills the configured store, so it is useful against Qdrant, while in-memory it only reports counts. The MFA lockout query returns `mfa-recovery` in the top 3.
