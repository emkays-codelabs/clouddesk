# ADR-0005: The vector store sits behind a protocol

## Status

Accepted. Matches upstream ADR-03 in spirit. v1 does not offer a pgvector option.

## Context

Upstream ADR-03 makes Qdrant the default for native hybrid search and payload filters, with pgvector as a
low-operations alternative. CloudDesk must also run and be tested with no server and no API key.

## Decision

A `VectorStoreService` protocol (`add_documents`, `search`, `delete`, `count`, `health`) has two
implementations, `InMemoryVectorStore` and `QdrantVectorStore`, chosen by `VECTOR_STORE`. Nothing outside
`rag/` knows which is live. Offline, embeddings are a hashed bag of words with 384 dimensions.

## Consequences

- Tests and the demo run with the in-memory store; the cloud uses Qdrant Cloud.
- Changing the embedding model requires an admin reindex, which recreates the collection.
- The `/health/ready` vector-store check currently tests configuration only.
- Nothing of this exists yet. It is built in Phase 5.
