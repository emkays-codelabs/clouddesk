"""Turn text into vectors without a network or an API key.

Does: define the `Embeddings` protocol and `FakeEmbeddings`, a deterministic hashed bag of words
(lower-cased tokens hashed into `dimensions` buckets, then L2-normalised) so similar wording scores
high offline.
Must NOT: call a network or LLM, know about tickets, customers or workflows, or import
`app.repositories` / `app.models`.
"""

import hashlib
import math
import re
from typing import Protocol

_TOKEN = re.compile(r"[a-z0-9]+")


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
