"""Knowledge routes (docs/design/06_API_CONTRACT.md, Knowledge base). HTTP only."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_role
from app.schemas.knowledge import (
    Article,
    ArticleDetail,
    ReindexResponse,
    SearchRequest,
    SearchResponse,
)
from app.services import knowledge_service

router = APIRouter(
    prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(get_current_user)]
)


@router.get("/articles", response_model=list[Article])
async def list_articles(search: str | None = None, category: str | None = None) -> list[Article]:
    return await knowledge_service.list_articles(search=search, category=category)


@router.get("/articles/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: str) -> ArticleDetail:
    try:
        return await knowledge_service.get_article(article_id)
    except knowledge_service.ArticleNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Article not found") from None


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest) -> SearchResponse:
    return await knowledge_service.search(body)


@router.post(
    "/reindex", response_model=ReindexResponse, dependencies=[Depends(require_role("admin"))]
)
async def reindex() -> ReindexResponse:
    return await knowledge_service.reindex()
