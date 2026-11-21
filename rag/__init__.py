"""Retrieval-augmented generation for CloudDesk knowledge articles.

Does: loads knowledge articles, chunks them, and (in later tasks) embeds, indexes and retrieves.
Must NOT: know about tickets, customers or workflows, or import `app.repositories`/`app.models`.
Callers pass in plain text and filters; `rag/` returns evidence.
"""
