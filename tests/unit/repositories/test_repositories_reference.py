from app.repositories.reference import (
    IncidentRepository,
    ProductRepository,
    SupportArticleRepository,
)
from app.schemas.common import Category


async def test_list_active_excludes_resolved_incidents(session, tenants):
    repo = IncidentRepository(session)
    live = await repo.create(title="SSO outage", status="investigating")
    await repo.create(title="Old", status="resolved")
    await session.commit()
    assert [i.id for i in await repo.list_active()] == [live.id]


async def test_products_round_trip(session, tenants):
    repo = ProductRepository(session)
    await repo.create(slug="storage", name="Storage")
    await session.commit()
    assert [p.slug for p in await repo.list()] == ["storage"]


async def test_upsert_by_slug_does_not_duplicate(session, tenants):
    repo = SupportArticleRepository(session)
    cat = Category.login_issue
    first = await repo.upsert_by_slug("sso", title="SSO", category=cat, content="v1")
    second = await repo.upsert_by_slug("sso", title="SSO 2", category=cat, content="v2")
    await session.commit()
    assert first.id == second.id
    items = await repo.list()
    assert len(items) == 1 and items[0].content == "v2" and items[0].title == "SSO 2"
    assert (await repo.get(first.id)).slug == "sso"


async def test_article_category_and_search_filters(session, tenants):
    repo = SupportArticleRepository(session)
    await repo.upsert_by_slug("sso", title="SSO", category=Category.login_issue, content="saml")
    await repo.upsert_by_slug("refund", title="Refunds", category=Category.billing, content="money")
    await session.commit()
    assert [a.slug for a in await repo.list(category=Category.billing)] == ["refund"]
    assert [a.slug for a in await repo.list(search="SAML")] == ["sso"]
