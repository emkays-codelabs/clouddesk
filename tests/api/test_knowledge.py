"""P5-4 (F5): knowledge API - list, read, search, admin-only reindex."""

MFA_QUERY = "Locked out after too many MFA attempts, changed phones"


def test_list_articles_returns_the_15_articles(client, viewer_headers):
    r = client.get("/api/v1/knowledge/articles", headers=viewer_headers)

    assert r.status_code == 200
    items = r.json()
    assert len(items) == 15
    assert {"id", "slug", "title", "category", "tags", "summary", "updated_at"} <= items[0].keys()


def test_list_filters_by_category_and_search(client, agent_headers):
    by_cat = client.get("/api/v1/knowledge/articles?category=login_issue", headers=agent_headers)
    by_text = client.get("/api/v1/knowledge/articles?search=rate%20limit", headers=agent_headers)

    assert by_cat.status_code == 200 and by_cat.json()
    assert all(a["category"] == "login_issue" for a in by_cat.json())
    assert "api-rate-limits" in [a["id"] for a in by_text.json()]


def test_get_article_returns_content(client, viewer_headers):
    r = client.get("/api/v1/knowledge/articles/mfa-recovery", headers=viewer_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["id"] == body["slug"] == "mfa-recovery"
    assert "recovery code" in body["content"].lower()


def test_unknown_article_is_404(client, viewer_headers):
    r = client.get("/api/v1/knowledge/articles/nope", headers=viewer_headers)

    assert r.status_code == 404
    assert r.json() == {"detail": "Article not found"}


def test_search_returns_the_mfa_article_in_the_top_3(client, agent_headers):
    r = client.post("/api/v1/knowledge/search", json={"query": MFA_QUERY}, headers=agent_headers)

    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "hybrid"
    assert body["took_ms"] >= 0
    assert "mfa-recovery" in [e["article_id"] for e in body["results"][:3]]
    assert body["results"][0]["source"].startswith("kb://")


def test_search_honours_mode_and_top_k_and_validates(client, viewer_headers):
    ok = client.post(
        "/api/v1/knowledge/search",
        json={"query": MFA_QUERY, "mode": "keyword", "top_k": 2},
        headers=viewer_headers,
    )
    bad = client.post(
        "/api/v1/knowledge/search",
        json={"query": MFA_QUERY, "mode": "magic"},
        headers=viewer_headers,
    )

    assert ok.status_code == 200 and ok.json()["mode"] == "keyword"
    assert len(ok.json()["results"]) <= 2
    assert bad.status_code == 422


def test_reindex_is_admin_only(client, agent_headers, viewer_headers, admin_headers):
    assert client.post("/api/v1/knowledge/reindex", headers=agent_headers).status_code == 403
    assert client.post("/api/v1/knowledge/reindex", headers=viewer_headers).status_code == 403

    r = client.post("/api/v1/knowledge/reindex", headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["indexed"] > 15


def test_search_still_works_after_reindex(client, admin_headers):
    client.post("/api/v1/knowledge/reindex", headers=admin_headers)

    r = client.post("/api/v1/knowledge/search", json={"query": MFA_QUERY}, headers=admin_headers)

    assert "mfa-recovery" in [e["article_id"] for e in r.json()["results"][:3]]


def test_every_knowledge_route_needs_a_token(client):
    assert client.get("/api/v1/knowledge/articles").status_code == 401
    assert client.get("/api/v1/knowledge/articles/mfa-recovery").status_code == 401
    assert client.post("/api/v1/knowledge/search", json={"query": "x"}).status_code == 401
    assert client.post("/api/v1/knowledge/reindex").status_code == 401


def test_startup_indexes_the_knowledge_base_into_an_empty_store():
    import asyncio

    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.main import create_app
    from rag.vector_store import get_vector_store, reset_vector_store

    reset_vector_store()
    with TestClient(create_app()):
        count = asyncio.run(get_vector_store(get_settings()).count())

    assert count > 15
