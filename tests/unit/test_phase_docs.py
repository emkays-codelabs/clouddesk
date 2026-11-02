"""P1-8: the phase-documentation spec has a trigger that cannot silently drift away from it."""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "09_PHASE_DOCUMENTATION.md"
SKILL = ROOT / ".claude" / "skills" / "phase-docs" / "SKILL.md"
RULES = ROOT / ".claude" / "rules"
DELEGATION = RULES / "cost-and-delegation.md"
PLAN = ROOT / "PLAN.md"


def _frontmatter(path: pathlib.Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: frontmatter must start on line 1"
    block = text[4 : text.index("\n---", 4)]
    return {
        k.strip(): v.strip()
        for k, v in (ln.split(":", 1) for ln in block.splitlines() if ":" in ln)
    }


def _spec_outputs() -> list[tuple[str, str]]:
    """(folder, file stem after 'PhaseN_') for each of the four documents the spec defines."""
    spec = SPEC.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"`internal/([A-Za-z_]+)/PhaseN_([A-Za-z_]+\.md)`", spec)))


class TestTheSpec:
    def test_it_is_complete_and_carries_no_cut_off_marker(self):
        spec = SPEC.read_text(encoding="utf-8")

        assert "This copy ends here" not in spec
        assert "FINAL INSTRUCTION TO THE CODING AGENT" in spec  # its last section
        assert "### Category M" in spec  # the last question category

    def test_it_defines_exactly_four_documents(self):
        assert [folder for folder, _ in _spec_outputs()] == [
            "Infra_design_evolution",
            "QnA",
            "design_evolution",
            "explain_codebase",
        ]


class TestTheSkill:
    def test_it_is_a_forked_on_demand_skill_with_a_real_agent(self):
        fm = _frontmatter(SKILL)

        assert fm["name"] == "phase-docs"
        assert fm["context"] == "fork"
        assert fm["agent"] == "general-purpose"  # a built-in agent, so it always exists
        assert fm["background"] == "false"  # the caller needs the result
        assert fm["disable-model-invocation"] == "true"  # it writes files; only the owner starts it

    def test_it_reads_the_spec_and_the_spec_exists(self):
        assert "docs/09_PHASE_DOCUMENTATION.md" in SKILL.read_text(encoding="utf-8")
        assert SPEC.exists()

    def test_it_names_every_output_folder_and_file_the_spec_defines(self):
        skill = SKILL.read_text(encoding="utf-8")

        missing = [
            f"internal/{folder}/ ... {stem}"
            for folder, stem in _spec_outputs()
            if f"internal/{folder}/" not in skill or stem not in skill
        ]

        assert missing == []

    def test_it_covers_every_question_category_the_spec_defines(self):
        categories = re.findall(r"^### Category ([A-Z]):", SPEC.read_text(encoding="utf-8"), re.M)
        skill = SKILL.read_text(encoding="utf-8")

        assert categories, "the spec defines no question categories"
        assert categories == [
            chr(ord("A") + i) for i in range(len(categories))
        ]  # A, B, C ... no gap
        assert f"A to {categories[-1]}" in skill

    def test_it_does_not_tell_the_agent_the_spec_is_unfinished_once_it_is_complete(self):
        assert "incomplete" not in SKILL.read_text(encoding="utf-8").lower()

    def test_it_stays_small_because_the_spec_is_read_only_when_it_runs(self):
        assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 40


class TestTheTrigger:
    def test_the_delegation_rule_lists_the_skill(self):
        assert "/phase-docs" in DELEGATION.read_text(encoding="utf-8")

    def test_the_plan_makes_the_documents_a_requirement_of_every_phase(self):
        plan = PLAN.read_text(encoding="utf-8")

        # The sentence that makes it a requirement, not merely a mention of the skill or the spec.
        assert "not done until its four documents exist" in plan
        assert "/phase-docs" in plan
        assert "09_PHASE_DOCUMENTATION" in plan

    def test_no_rule_loads_the_spec_into_every_session(self):
        # An unscoped rule loads in full every session; the 800-line spec must stay in docs/.
        too_long = {
            p.name: len(p.read_text(encoding="utf-8").splitlines())
            for p in RULES.glob("*.md")
            if len(p.read_text(encoding="utf-8").splitlines()) > 30
        }

        assert too_long == {}


CLAUDE_MD = ROOT / "CLAUDE.md"
SKILLS_DIR = ROOT / ".claude" / "skills"


def _documented_commands() -> set[str]:
    """The slash commands CLAUDE.md section 14 lists on its 'In Claude Code' line."""
    line = next(
        ln
        for ln in CLAUDE_MD.read_text(encoding="utf-8").splitlines()
        if ln.startswith("In Claude Code")
    )
    return set(re.findall(r"`/([a-z][a-z-]*)", line))


class TestMidPhaseTrigger:
    """Documents are updated as a phase goes (spec section 7, Step 4), not only when it ends."""

    PHRASE = "an architectural boundary, networking or an important flow"

    def test_the_task_completion_rule_in_claude_md_requires_it(self):
        text = CLAUDE_MD.read_text(encoding="utf-8")
        rule = next(ln for ln in text.splitlines() if ln.startswith("16. "))

        assert self.PHRASE in rule
        assert "internal/" in rule

    def test_the_done_when_checklist_in_the_skill_requires_it(self):
        skill = (SKILLS_DIR / "clouddesk-support" / "SKILL.md").read_text(encoding="utf-8")

        assert self.PHRASE in skill
        assert "internal/" in skill


class TestClaudeMd:
    """CLAUDE.md is the source of truth, so it must describe the setup that actually exists."""

    def test_every_command_it_lists_is_a_real_skill(self):
        skills = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}

        assert _documented_commands() - skills == set()

    def test_every_project_skill_is_listed(self):
        # clouddesk-support is loaded by Claude itself, not typed as a command.
        skills = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()} - {"clouddesk-support"}

        assert skills - _documented_commands() == set()

    def test_the_layout_names_what_is_in_the_claude_folder_and_the_documents_folder(self):
        text = CLAUDE_MD.read_text(encoding="utf-8")

        assert "agents/ · skills/ · rules/ · hooks/pre-commit.sh" in text
        assert "internal/" in text
        assert "08_CLAUDE_SETUP.md" in text
        assert "09_PHASE_DOCUMENTATION.md" in text

    def test_a_phase_is_not_done_until_its_documents_exist(self):
        text = CLAUDE_MD.read_text(encoding="utf-8")

        assert "A phase is not done until its four documents exist" in text
        assert "docs/09_PHASE_DOCUMENTATION.md" in text

    def test_the_cost_rule_points_at_a_file_that_exists(self):
        text = CLAUDE_MD.read_text(encoding="utf-8")

        assert ".claude/rules/cost-and-delegation.md" in text
        assert DELEGATION.exists()

    def test_the_design_comparison_table_lists_chunking(self):
        assert "| Chunking |" in CLAUDE_MD.read_text(encoding="utf-8")
