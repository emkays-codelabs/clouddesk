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

    def test_it_admits_the_spec_is_incomplete_instead_of_inventing_the_rest(self):
        assert "incomplete" in SKILL.read_text(encoding="utf-8").lower()

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
