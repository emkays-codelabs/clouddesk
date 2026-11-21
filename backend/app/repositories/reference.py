"""Reference data: incidents, products and support articles."""

from __future__ import annotations

from typing import Any

from app.models.entities import Incident, Product, SupportArticle
from app.repositories.base import ScopedRepository, contains_any
from app.schemas.common import Category


class IncidentRepository(ScopedRepository[Incident]):
    model = Incident

    async def create(self, **fields: Any) -> Incident:
        return await self._add(Incident(**fields))

    async def list_active(self) -> list[Incident]:
        stmt = self._select(Incident.status != "resolved").order_by(Incident.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class ProductRepository(ScopedRepository[Product]):
    model = Product

    async def create(self, **fields: Any) -> Product:
        return await self._add(Product(**fields))

    async def list(self) -> list[Product]:
        stmt = self._select().order_by(Product.slug)
        return list((await self.session.execute(stmt)).scalars().all())


class SupportArticleRepository(ScopedRepository[SupportArticle]):
    model = SupportArticle

    async def upsert_by_slug(self, slug: str, **fields: Any) -> SupportArticle:
        result = await self.session.execute(self._select(SupportArticle.slug == slug))
        row = result.scalar_one_or_none()
        if row is None:
            return await self._add(SupportArticle(slug=slug, **fields))
        for key, value in fields.items():
            setattr(row, key, value)
        await self.session.flush()
        return row

    async def get(self, id: str) -> SupportArticle | None:
        return await self._get(id)

    async def list(
        self, search: str | None = None, category: Category | None = None
    ) -> list[SupportArticle]:
        stmt = self._select().order_by(SupportArticle.slug)
        if category is not None:
            stmt = stmt.where(SupportArticle.category == category)
        if search:
            stmt = stmt.where(
                contains_any(
                    search,
                    SupportArticle.title,
                    SupportArticle.summary,
                    SupportArticle.content,
                )
            )
        return list((await self.session.execute(stmt)).scalars().all())
