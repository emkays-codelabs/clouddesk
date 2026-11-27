"""Turn text into vectors: offline by default, Euron's embeddings endpoint when asked (P9-10).

Does: define the `Embeddings` protocol; `FakeEmbeddings`, a deterministic hashed bag of words
(lower-cased tokens hashed into `dimensions` buckets, then L2-normalised) so similar wording scores
high offline; and `EuronEmbeddings`, which sends batches to an OpenAI-compatible embeddings
endpoint,
reads the vector size from the first response and refuses a size that differs from the configured
`dimensions` (a clear `EmbeddingError`). Settings arrive as constructor arguments; the selector that
reads them is in `backend/app/services/knowledge_service.py`.
Must NOT: import anything from `app` (settings come in as arguments), know about tickets, customers
or workflows, import `app.repositories` / `app.models`, or put a provider message (which could echo
a key) into an error. `EuronEmbeddings` is the only network call in `rag/`, and the one place
besides `app/core/llm.py` that imports the OpenAI SDK.
"""

import hashlib
import math
import re
from typing import Protocol

_TOKEN = re.compile(r"[a-z0-9]+")

EURON_EMBEDDING_MODEL = "euri-embedding"
DEFAULT_BATCH_SIZE = 64
REQUEST_TIMEOUT_SECONDS = 60.0


class EmbeddingError(RuntimeError):
    """The embeddings could not be produced, or were not the size the index expects."""


class Embeddings(Protocol):
    dimensions: int

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddings:
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_query(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for token in _TOKEN.findall(text.lower()):
            # md5, not hash(): Python's str hash is salted per process and would break determinism.
            bucket = int.from_bytes(hashlib.md5(token.encode()).digest()[:8], "big")
            vec[bucket % self.dimensions] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm else vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]


class EuronEmbeddings:
    """Embeddings over an OpenAI-compatible endpoint (Euron euri). Synchronous, as the protocol."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        model: str = EURON_EMBEDDING_MODEL,
        dimensions: int = 384,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        from openai import OpenAI

        self.dimensions = dimensions
        self.model = model or EURON_EMBEDDING_MODEL
        self.batch_size = max(1, batch_size)
        self.detected_dimensions: int | None = None
        # max_retries=0: a failed batch is an error, not a silent second billing.
        self._client = OpenAI(
            api_key=api_key, base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=0
        )

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(model=self.model, input=texts)
        except Exception as exc:  # the provider's message may echo credentials: name the class only
            raise EmbeddingError(f"embeddings request failed: {type(exc).__name__}") from exc
        items = sorted(response.data, key=lambda d: d.index)
        if len(items) != len(texts):
            raise EmbeddingError(
                f"the embeddings endpoint returned {len(items)} vectors for {len(texts)} texts"
            )
        vectors = [[float(x) for x in item.embedding] for item in items]
        if self.detected_dimensions is None:
            self.detected_dimensions = len(vectors[0])
        if self.detected_dimensions != self.dimensions:
            raise EmbeddingError(
                f"model {self.model!r} returns {self.detected_dimensions}-dimensional vectors but "
                f"EMBEDDING_DIMENSIONS is {self.dimensions}; set EMBEDDING_DIMENSIONS="
                f"{self.detected_dimensions} and reindex"
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # The endpoint rejects empty input, so an empty text is sent as one space.
        prepared = [t if t.strip() else " " for t in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(prepared), self.batch_size):
            vectors += self._embed_batch(prepared[start : start + self.batch_size])
        return vectors
