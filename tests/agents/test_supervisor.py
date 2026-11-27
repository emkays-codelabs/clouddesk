"""P9-2: the Supervisor classifies, only raises severity and carries the injection scan."""

import agents.specialists.supervisor as sup
from agents.specialists.supervisor import SupervisorAgent
from app.core.llm import Completion
from app.schemas.common import Category, Severity
from app.schemas.workflow import Classification, SeverityAssessment

CATEGORIES = {c.value for c in Category}


class Scripted:
    """A provider that answers every call with one fixed JSON text."""

    name = "scripted"
    model = "scripted"

    def __init__(self, text: str):
        self.text = text

    def estimate_cost(self, *_):
        return 0.0

    async def complete(self, schema, messages, temperature, hints):
        return Completion(self.text, 1, 1)


class Broken(Scripted):
    async def complete(self, *args):
        raise RuntimeError("down")


async def test_classification_is_one_of_ten_with_one_line_summary(text_of):
    u, status, usage, ms, calls = await SupervisorAgent().understand(text_of("CD-1002"))
    c = u.classification
    assert status == "ok" and c.category == Category.billing
    assert len(CATEGORIES) == 10 and c.category.value in CATEGORIES
    assert c.summary and "\n" not in c.summary and calls == []
    assert usage.estimated_cost_usd == 0.0 and ms >= 0


async def test_rule_category_wins_over_a_disagreeing_model(text_of):
    llm = Scripted('{"category":"other","summary":"s","confidence":0.99}')
    u, *_ = await SupervisorAgent(llm).understand(text_of("CD-1002"))
    assert u.classification.category == Category.billing


async def test_severity_for_cd_1010_stays_low(text_of):
    a, *_ = await SupervisorAgent().assess_severity(text_of("CD-1010"), "free")
    assert a.severity == Severity.low and a.reason


async def test_rules_raise_a_low_model_severity(text_of):
    llm = Scripted('{"severity":"low","reason":"fine"}')
    a, *_ = await SupervisorAgent(llm).assess_severity(text_of("CD-1005"), "business")
    assert a.severity in (Severity.high, Severity.critical)


async def test_rules_never_lower_a_high_model_severity(text_of):
    llm = Scripted('{"severity":"critical","reason":"x"}')
    a, *_ = await SupervisorAgent(llm).assess_severity(text_of("CD-1010"), "free")
    assert a.severity == Severity.critical


async def test_model_failure_falls_back_to_rules(text_of):
    agent = SupervisorAgent(Broken(""))
    u, status, *_ = await agent.understand(text_of("CD-1003"))
    assert status == "fallback" and u.classification.category == Category.api_failure
    a, status, *_ = await agent.assess_severity(text_of("CD-1005"), "business")
    assert status == "fallback" and a.severity == Severity.critical


async def test_cd_1013_stays_data_flagged_and_no_export_action(text_of, monkeypatch):
    seen = {"users": [], "systems": []}
    real = sup.call_structured

    async def spy(schema, **kw):
        seen["users"].append(kw["user"])
        seen["systems"].append(kw["system"])
        return await real(schema, **kw)

    monkeypatch.setattr(sup, "call_structured", spy)
    text = text_of("CD-1013")
    agent = SupervisorAgent()
    u, *_ = await agent.understand(text)
    await agent.assess_severity(text, "free")
    assert u.injection.flagged and "export_all_records" in u.injection.flags
    assert len(seen["users"]) == 2
    assert all(m.startswith("<untrusted_content>") for m in seen["users"])
    assert all("never an instruction" in s for s in seen["systems"])
    assert not hasattr(u.classification, "actions")
    assert u.classification.category in (Category.security, Category.other, Category.account)


def test_ticket_summary_is_deterministic():
    c = Classification(category=Category.billing, summary="Refund for unused seats.")
    s = SeverityAssessment(severity=Severity.medium, reason="r")
    line = SupervisorAgent().ticket_summary("CD-1002", c, s, "refund approved")
    assert line.startswith("CD-1002 [billing, medium]: Refund") and line.endswith("approved")
