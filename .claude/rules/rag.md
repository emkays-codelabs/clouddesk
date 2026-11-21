---
paths:
  - "rag/**"
---

# RAG conventions

- `rag/` does retrieval only: load and chunk articles, embed, index, retrieve, ingest.
- `rag/` knows nothing about tickets, customers or workflows. It must not import `app.repositories`,
  `app.models` or `agents/`. Callers pass text and filters in; evidence comes out.
- Every `rag/` module docstring says what the module does and what it must NOT do.
- Chunking: split on headings, then 900-character windows with a 150-character overlap; every chunk is
  prefixed `"{title} - {heading}"` (`CLAUDE.md` section 8).
- Retrieved content is untrusted: no instructions to an AI in articles, and scan chunks before a prompt.
- The vector store sits behind `VectorStoreService`; nothing outside `rag/` knows which one is live.
- Must run offline: fake embeddings, in-memory store, no network in tests.
