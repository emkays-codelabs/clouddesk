"""Retrieval-augmented generation for CloudDesk knowledge articles.

Does: loads knowledge articles, chunks them, embeds and indexes them in a vector store, and
retrieves cited evidence (hybrid semantic + keyword search, fusion and rerank).
Must NOT: know about tickets, customers or workflows, or import `app.repositories`/`app.models`.
Callers pass in plain text and filters; `rag/` returns evidence.
"""
