"""P1-13: the README is numbered, navigable and cannot quietly drift from the plan it summarises."""

import pathlib
import re

import pytest

from scripts.check_phase_docs import mermaid_problems

ROOT = pathlib.Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")
PLAN = (ROOT / "PLAN.md").read_text(encoding="utf-8").replace("\r\n", "\n")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8").replace("\r\n", "\n")

TITLE = "CloudDesk AI"
TAGLINE = "Intelligent Resolution. Human-Controlled Decisions."
CATEGORY = "AI-Powered Customer Support & Ticket Investigation Platform"
BACK_TO_TOP = "[↑ Back to top](#clouddesk-ai)"


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s", "-", text)


def _outside_fences(text: str) -> list[str]:
    lines, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return lines


LINES = _outside_fences(README)
H2 = [
    (i, m.group(1), m.group(2))
    for i, ln in enumerate(LINES)
    if (m := re.match(r"^## (\d+)\. (.+)$", ln))
]
H3 = [
    (i, m.group(1), m.group(2), m.group(3))
    for i, ln in enumerate(LINES)
    if (m := re.match(r"^### (\d+)\.(\d+) (.+)$", ln))
]
ALL_HEADINGS = [ln.lstrip("#").strip() for ln in LINES if re.match(r"^#{1,6} ", ln)]
ANCHORS = {slug(h) for h in ALL_HEADINGS}


class TestIdentity:
    def test_the_title_is_the_product_name(self):
        assert README.splitlines()[0] == f"# {TITLE}"

    def test_the_tagline_and_category_are_stated_near_the_top(self):
        top = "\n".join(README.splitlines()[:15])

        assert TAGLINE in top
        assert CATEGORY in top

    def test_it_says_the_repository_and_package_are_still_named_clouddesk(self):
        # The product name changed; the code did not. A reader should not be left to wonder.
        assert "`clouddesk`" in README


class TestNumbering:
    def test_the_sections_are_numbered_from_1_with_no_gap(self):
        numbers = [int(n) for _, n, _ in H2]

        assert numbers, "no numbered sections found"
        assert numbers == list(range(1, len(numbers) + 1))

    def test_the_subsections_are_numbered_within_their_section(self):
        problems = []
        parent = 0
        expected_child = 1
        events = sorted(
            [(i, "h2", int(n)) for i, n, _ in H2]
            + [(i, "h3", (int(a), int(b))) for i, a, b, _ in H3]
        )
        for _, kind, value in events:
            if kind == "h2":
                parent, expected_child = value, 1
            else:
                section, child = value
                if section != parent or child != expected_child:
                    problems.append(
                        f"{section}.{child} found where {parent}.{expected_child} was expected"
                    )
                expected_child += 1

        assert problems == []


class TestTableOfContents:
    def _toc_lines(self) -> list[str]:
        start = next(i for i, ln in enumerate(LINES) if ln == "## Table of contents")
        first_section = H2[0][0]
        assert start < first_section, "the table of contents must come before section 1"
        return LINES[start + 1 : first_section]

    def test_it_exists_and_comes_before_the_first_section(self):
        assert self._toc_lines()

    def test_it_lists_every_numbered_section_in_order(self):
        entries = [
            m.groups()
            for ln in self._toc_lines()
            if (m := re.match(r"^(\d+)\. \[(.+)\]\(#(.+)\)$", ln))
        ]

        assert [(int(n), title) for n, title, _ in entries] == [
            (int(n), title) for _, n, title in H2
        ]

    def test_every_entry_links_to_a_heading_that_exists(self):
        targets = re.findall(r"\]\(#([^)]+)\)", "\n".join(self._toc_lines()))

        assert targets
        assert [t for t in targets if t not in ANCHORS] == []

    def test_every_numbered_heading_appears_in_it(self):
        toc = "\n".join(self._toc_lines())
        missing = [
            f"{n}. {title}" for _, n, title in H2 if f"(#{slug(f'{n}. {title}')})" not in toc
        ]
        missing += [
            f"{a}.{b} {title}"
            for _, a, b, title in H3
            if f"(#{slug(f'{a}.{b} {title}')})" not in toc
        ]

        assert missing == []

    def test_each_subsection_entry_shows_the_same_label_as_its_heading(self):
        shown = re.findall(r"^   - \[(\d+\.\d+ .+?)\]\(#.+\)$", "\n".join(self._toc_lines()), re.M)

        assert shown == [f"{a}.{b} {title}" for _, a, b, title in H3]


class TestBackToTop:
    def test_the_link_points_at_the_title_and_the_title_exists(self):
        assert slug(TITLE) == "clouddesk-ai"
        assert "clouddesk-ai" in ANCHORS

    def test_every_numbered_section_ends_with_one(self):
        body = "\n".join(LINES)
        sections = re.split(r"^## \d+\. ", body, flags=re.M)[1:]
        without = [i + 1 for i, text in enumerate(sections) if BACK_TO_TOP not in text]

        assert without == []


class TestLinks:
    def test_every_in_page_link_resolves_to_a_heading(self):
        broken = [a for a in re.findall(r"\]\(#([^)]+)\)", "\n".join(LINES)) if a not in ANCHORS]

        assert broken == []


class TestNoDrift:
    def _phase_rows(self, text: str) -> dict[int, tuple[str, str]]:
        rx = r"^\| (\d+) \| ([^|]+?) \| (not started|in progress|implemented|validated locally) \|$"
        return {int(n): (name, status) for n, name, status in re.findall(rx, text, re.M)}

    def test_the_roadmap_matches_the_plan_exactly(self):
        assert self._phase_rows(README) == self._phase_rows(PLAN)
        assert len(self._phase_rows(README)) == 14

    def test_every_make_command_it_shows_is_a_real_target(self):
        targets = set(re.findall(r"^([a-z]+):", MAKEFILE, re.M))
        used = set(re.findall(r"`make ([a-z]+)`", README)) | set(
            re.findall(r"^make ([a-z]+)\b", README, re.M)
        )

        assert used, "the README shows no make commands"
        assert used - targets == set()

    def test_it_does_not_claim_the_project_is_deployed(self):
        assert re.search(r"nothing is deployed|not deployed", README, re.I)

    def test_its_diagrams_are_structurally_sound(self):
        assert mermaid_problems(README) == []
        assert re.search(r"^```mermaid$", README, re.M)


@pytest.mark.parametrize("heading", ["Table of contents"])
def test_the_unnumbered_contents_heading_is_the_only_unnumbered_h2(heading: str):
    unnumbered = [ln for ln in LINES if re.match(r"^## (?!\d+\. )", ln)]

    assert unnumbered == [f"## {heading}"]


class TestItPointsAtTheRealFolders:
    def test_every_folder_it_names_in_where_to_find_things_exists(self):
        section = README.split("## 7. Where to find things")[1].split("## 8.")[0]
        named = set(re.findall(r"`(docs/[a-z0-9_]+/|internal/)`", section))

        assert {"docs/design/", "docs/adr/", "internal/"} <= named
        assert [n for n in named if not (ROOT / n.rstrip("/")).exists()] == []

    def test_it_explains_the_branch_names_and_the_personal_overrides_file(self):
        assert "### 6.3 Branches and pull requests" in README
        for prefix in ("feature/<name>", "docs/<name>", "chore/<name>"):
            assert prefix in README
        assert "CLAUDE.local.md" in README

    def test_it_says_the_api_contract_describes_routes_that_are_not_built_yet(self):
        assert "not built yet" in README.split("docs/design/")[1].split("\n")[0].lower() or (
            "contract describes routes that are not built" in README
        )
