"""P5-1 (F5): articles load and chunk with the title-heading prefix and 900/150 windows."""

from pathlib import Path

import pytest

from app.schemas.common import Category
from rag.chunking import (
    OVERLAP,
    WINDOW,
    Article,
    chunk_article,
    load_article_files,
    split_windows,
)

KB_DIR = Path(__file__).resolve().parents[2] / "sample_data" / "knowledge_base"


@pytest.fixture(scope="module")
def articles():
    return load_article_files(KB_DIR)


@pytest.fixture(scope="module")
def chunks(articles):
    return [c for a in articles for c in chunk_article(a)]


def test_loading_yields_fifteen_articles(articles):
    assert len(articles) == 15
    assert len({a.slug for a in articles}) == 15


def test_front_matter_is_complete_and_categories_are_valid(articles):
    valid = {c.value for c in Category}
    for a in articles:
        assert a.title.strip() and a.summary.strip(), a.slug
        assert a.category in valid, a.slug
        assert a.tags and all(isinstance(t, str) for t in a.tags), a.slug


def test_demo_topics_each_have_an_article(articles):
    by_slug = {a.slug: a for a in articles}
    assert by_slug["mfa-recovery"].category == "login_issue"
    assert by_slug["payment-disputes"].category == "billing"
    assert by_slug["api-rate-limits"].category == "api_failure"
    assert {a.category for a in articles} >= {"security", "integration", "feature_request"}


def test_every_chunk_has_prefix_and_body(chunks):
    assert chunks
    for c in chunks:
        assert c.text.startswith(f"{c.title} - {c.heading}\n"), c
        assert c.body.strip(), c
        assert c.text == f"{c.title} - {c.heading}\n{c.body}"


def test_windows_respect_size_and_overlap(chunks):
    by_section: dict[tuple[str, str], list] = {}
    for c in chunks:
        assert len(c.body) <= WINDOW
        by_section.setdefault((c.article_slug, c.heading), []).append(c)
    for group in by_section.values():
        for prev, nxt in zip(group, group[1:], strict=False):
            assert prev.body[-OVERLAP:] == nxt.body[:OVERLAP]


def test_split_windows_long_text_overlaps_and_covers():
    text = "".join(str(i % 10) for i in range(2000))
    wins = split_windows(text)
    assert all(len(w) <= WINDOW for w in wins)
    assert len(wins) == 3
    assert wins[0][-OVERLAP:] == wins[1][:OVERLAP]
    assert wins[-1].endswith(text[-10:])
    assert split_windows("short") == ["short"]
    assert split_windows("   ") == []


def test_chunks_cover_each_article_and_have_ids(chunks, articles):
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))
    assert {c.article_slug for c in chunks} == {a.slug for a in articles}
    assert len(chunks) > len(articles)


def test_mfa_article_serves_cd_1012(articles):
    mfa = next(a for a in articles if a.slug == "mfa-recovery")
    text = mfa.body.lower()
    assert "new phone" in text and "recovery code" in text and "locked" in text


def test_missing_front_matter_is_rejected(tmp_path):
    (tmp_path / "bad.md").write_text("# No front matter\n\n## A\nBody\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_article_files(tmp_path)


def test_rag_modules_state_what_they_must_not_do():
    import rag
    import rag.chunking as mod

    for m in (rag, mod):
        assert "must not" in (m.__doc__ or "").lower()


def test_rag_does_not_import_ticket_or_repository_code():
    src = (Path(__file__).resolve().parents[2] / "rag").glob("*.py")
    for f in src:
        imports = [
            ln
            for ln in f.read_text(encoding="utf-8").splitlines()
            if ln.startswith(("import ", "from "))
        ]
        assert not [ln for ln in imports if ln.split()[1].split(".")[0] in ("app", "agents")], f


def test_long_section_is_windowed_with_overlap_and_prefix():
    body = "## Long\n" + " ".join(f"word{i}" for i in range(600))
    article = Article("long", "Long article", "other", ["x"], "s", body)
    made = chunk_article(article)
    assert len(made) >= 3
    for prev, nxt in zip(made, made[1:], strict=False):
        assert prev.body[-OVERLAP:] == nxt.body[:OVERLAP]
    assert all(len(c.body) <= WINDOW for c in made)
    assert all(c.text.startswith("Long article - Long\n") for c in made)
