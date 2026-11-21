"""Knowledge response types (docs/design/06_API_CONTRACT.md, Knowledge base)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Article(BaseModel):
    id: str
    slug: str
    title: str
    category: str
    tags: list[str]
    summary: str
    updated_at: datetime


class ArticleDetail(Article):
    content: str


class Evidence(BaseModel):
    id: str
    title: str
    source: str
    snippet: str
    score: float
    url: str | None = None
    article_id: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Literal["hybrid", "semantic", "keyword"] = "hybrid"


class SearchResponse(BaseModel):
    results: list[Evidence]
    mode: Literal["hybrid", "semantic", "keyword"]
    took_ms: int


class ReindexResponse(BaseModel):
    indexed: int
