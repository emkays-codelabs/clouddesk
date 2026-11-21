# Phase 5: system design evolution

> **Status of this phase:** in progress. P5-1 is implemented and checked locally; P5-2 to P5-4 are not started. Nothing is deployed, and there are no embeddings, vector store, retriever or knowledge API yet.

---

## P5-1: knowledge articles and chunking

`rag/` is a new top-level package that knows nothing about tickets. `rag/chunking.py` loads the 15 articles in `sample_data/knowledge_base/` (YAML front-matter: title, category, tags, summary) and `chunk_article` splits each on headings, then into 900-character windows with a 150-character overlap. Every chunk's text is prefixed `"{title} - {heading}"`; `Chunk.body` holds the raw window so the size and overlap can be tested. Text before the first heading is filed under "Overview". Front-matter errors raise `ValueError` at load time. `pyyaml` is the one new dependency.

Boundary: `.claude/rules/rag.md` (`paths: rag/**`) and each module docstring state that `rag/` must not import ticket, repository or agent code. A test checks the imports.
