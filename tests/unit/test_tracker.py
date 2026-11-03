"""P1-14: the task tracker cannot drift from itself, from PLAN.md, or from the status documents.

The counters in TASKS.md conflicted on three separate pull requests and were checked by hand each
time. These tests make the hand check a build failure.
"""

import collections
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8").replace("\r\n", "\n")


TASKS = _read("TASKS.md")
PLAN = _read("PLAN.md")
CLAUDE = _read("CLAUDE.md")
MEMORY = _read("MEMORY.md")

ROW = re.compile(
    r"^\| (P(\d+)-(\d+)) · (.+?) \| (.+?) \| `?([^|`]*)`? \| (Pending ❌|Completed ✅) \|$", re.M
)
ROWS = ROW.findall(TASKS)
DEFINITIONS = re.findall(r"^\*\*(P\d+-\d+) · (.+?)\*\*$", TASKS, re.M)
PHASE_ROW = re.compile(
    r"^\| (\d+) \| ([^|]+?) \| (not started|in progress|implemented|validated locally) \|$", re.M
)
BRANCH_PREFIXES = {"feature", "docs", "chore", "bugfix", "hotfix"}


class TestRowsAndDefinitions:
    def test_there_is_a_definition_for_every_row_and_a_row_for_every_definition(self):
        row_ids = [r[0] for r in ROWS]
        definition_ids = [d[0] for d in DEFINITIONS]

        assert sorted(row_ids) == sorted(definition_ids)

    def test_no_task_id_is_used_twice(self):
        ids = [r[0] for r in ROWS]

        assert [k for k, n in collections.Counter(ids).items() if n > 1] == []

    def test_a_row_and_its_definition_carry_the_same_title(self):
        titles = dict(DEFINITIONS)

        assert [r[0] for r in ROWS if titles.get(r[0], "").strip() != r[3].strip()] == []

    def test_every_needs_line_names_only_tasks_that_exist(self):
        ids = {r[0] for r in ROWS}
        problems = []
        for block in re.split(r"(?m)^\*\*(?=P\d+-\d+ · )", TASKS)[1:]:
            task = re.match(r"(P\d+-\d+)", block).group(1)
            needs = re.search(r"- \*\*Needs:\*\* (.+)", block)
            if not needs:
                problems.append(f"{task}: no Needs line")
                continue
            problems += [
                f"{task} needs {n}"
                for n in re.findall(r"P\d+-\d+", needs.group(1))
                if n not in ids or n == task
            ]

        assert problems == []

    def test_every_branch_uses_a_prefix_the_workflow_allows(self):
        prefixes = {r[5].strip().split("/")[0] for r in ROWS if r[5].strip() not in ("", "—")}

        assert prefixes <= BRANCH_PREFIXES

    def test_the_stated_branch_convention_covers_every_prefix_in_use(self):
        convention = TASKS.split("**Branch convention:**")[1].split("\n")[0]
        used = {r[5].strip().split("/")[0] for r in ROWS if r[5].strip() not in ("", "—")}

        assert [p for p in used if f"{p}/<name>" not in convention] == []

    def test_phase_1_tooling_tasks_are_all_mentioned_in_the_phase_1_introduction(self):
        intro = TASKS.split("## Phase 1 ")[1].split("#### Task definitions")[0]
        tooling = [r[0] for r in ROWS if r[1] == "1" and int(r[2]) >= 5]

        assert [t for t in tooling if t not in intro] == []


class TestCounters:
    def _progress(self) -> dict[int, tuple[int, int]]:
        found = re.findall(r"^\| (\d+) \| [^|]+ \| (\d+) \| (\d+) \|$", TASKS, re.M)
        return {int(a): (int(b), int(c)) for a, b, c in found}

    def test_each_phase_count_matches_its_rows(self):
        total = collections.Counter(int(r[1]) for r in ROWS)
        done = collections.Counter(int(r[1]) for r in ROWS if r[6].startswith("Completed"))

        assert self._progress() == {p: (total[p], done[p]) for p in total}

    def test_the_total_row_matches_the_rows(self):
        shown = re.search(r"\*\*Total\*\* \| \| \*\*(\d+)\*\* \| \*\*(\d+)\*\*", TASKS).groups()
        done = sum(1 for r in ROWS if r[6].startswith("Completed"))

        assert (int(shown[0]), int(shown[1])) == (len(ROWS), done)

    def test_the_finished_when_list_names_the_real_task_count(self):
        said = re.search(
            r"All (\d+) tasks are Completed ✅ and the Progress summary reads (\d+) of (\d+)", TASKS
        )

        assert [int(g) for g in said.groups()] == [len(ROWS)] * 3

    def test_the_honest_status_states_the_current_overall_progress(self):
        done = sum(1 for r in ROWS if r[6].startswith("Completed"))

        assert f"{done} of {len(ROWS)} tasks" in MEMORY


class TestPhaseStatusesAgree:
    def test_claude_md_and_plan_md_give_every_phase_the_same_status(self):
        plan = {int(n): (name, s) for n, name, s in PHASE_ROW.findall(PLAN)}
        claude = {int(n): (name, s) for n, name, s in PHASE_ROW.findall(CLAUDE)}

        assert len(plan) == 14
        assert claude == plan

    def test_the_progress_table_names_the_same_phases_as_plan_md(self):
        plan = {int(n): name for n, name, _ in PHASE_ROW.findall(PLAN)}
        progress = {
            int(n): name.strip()
            for n, name in re.findall(r"^\| (\d+) \| ([^|]+) \| \d+ \| \d+ \|$", TASKS, re.M)
        }

        assert progress == plan
