"""Load knowledge articles and split them into retrievable chunks.

Does: read `*.md` files with YAML front-matter (title, category, tags, summary), split each on
headings, then cut each section into 900-character windows with a 150-character overlap. Every
chunk is prefixed `"{title} - {heading}"` so short chunks stay retrievable.
Must NOT: know about tickets, customers or workflows, touch the database, call an LLM or embed
anything, or import `app.repositories` / `app.models`.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

WINDOW = 900
OVERLAP = 150

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_REQUIRED = ("title", "category", "tags", "summary")


@dataclass(frozen=True)
class Article:
    slug: str
    title: str
    category: str
    tags: list[str]
    summary: str
    body: str


@dataclass(frozen=True)
class Chunk:
    id: str
    article_slug: str
    title: str
    category: str
    heading: str
    index: int
    body: str
    tags: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return f"{self.title} - {self.heading}\n{self.body}"


def load_article_files(directory: Path | str) -> list[Article]:
    """Read every `*.md` article in `directory`, sorted by file name."""
    articles = []
    for path in sorted(Path(directory).glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = _FRONT_MATTER.match(raw)
        if not match:
            raise ValueError(f"{path.name}: missing YAML front-matter")
        meta = yaml.safe_load(match.group(1)) or {}
        missing = [k for k in _REQUIRED if not meta.get(k)]
        if missing:
            raise ValueError(f"{path.name}: front-matter missing {', '.join(missing)}")
        articles.append(
            Article(
                slug=path.stem,
                title=str(meta["title"]).strip(),
                category=str(meta["category"]).strip(),
                tags=[str(t) for t in meta["tags"]],
                summary=str(meta["summary"]).strip(),
                body=match.group(2).strip(),
            )
        )
    return articles


def split_sections(article: Article) -> list[tuple[str, str]]:
    """Split on headings into (heading, text) pairs, skipping empty sections."""
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    for line in article.body.splitlines():
        m = _HEADING.match(line)
        if m:
            sections.append((m.group(1), []))
        else:
            sections[-1][1].append(line)
    return [(h, "\n".join(lines).strip()) for h, lines in sections if "".join(lines).strip()]


def split_windows(text: str) -> list[str]:
    """Cut `text` into WINDOW-character windows, each overlapping the last by OVERLAP."""
    text = text.strip()
    if not text:
        return []
    windows, start = [], 0
    while True:
        end = min(start + WINDOW, len(text))
        windows.append(text[start:end])
        if end == len(text):
            return windows
        start = end - OVERLAP


def chunk_article(article: Article) -> list[Chunk]:
    """Chunk one article: heading split, then overlapping windows."""
    chunks = []
    for heading, text in split_sections(article):
        for window in split_windows(text):
            n = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{article.slug}#{n}",
                    article_slug=article.slug,
                    title=article.title,
                    category=article.category,
                    heading=heading,
                    index=n,
                    body=window,
                    tags=article.tags,
                )
            )
    return chunks
