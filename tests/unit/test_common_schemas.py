import re
from pathlib import Path

from app.schemas.common import Category, Channel, Severity, TicketStatus

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "design" / "06_API_CONTRACT.md"


def values(enum) -> list[str]:
    return [m.value for m in enum]


def test_categories_are_exactly_the_ten_in_the_spec():
    assert values(Category) == [
        "login_issue",
        "billing",
        "api_failure",
        "workspace_permissions",
        "storage_quota",
        "integration",
        "feature_request",
        "account",
        "security",
        "other",
    ]


def test_statuses_are_exactly_the_seven_in_the_spec():
    assert values(TicketStatus) == [
        "new",
        "in_progress",
        "waiting_on_customer",
        "waiting_on_approval",
        "escalated",
        "resolved",
        "closed",
    ]


def test_severities_are_exactly_the_four_in_the_spec():
    assert values(Severity) == ["low", "medium", "high", "critical"]


def test_channels_are_exactly_the_four_in_the_spec():
    assert values(Channel) == ["email", "chat", "web", "api"]


def _union(text: str) -> list[str]:
    return re.findall(r'"([a-z_]+)"', text)


def test_the_api_contract_lists_the_same_values():
    doc = CONTRACT.read_text(encoding="utf-8")
    for name, enum in (
        ("TicketStatus", TicketStatus),
        ("Severity", Severity),
        ("Category", Category),
    ):
        line = re.search(rf"type {name} = (.+);", doc).group(1)
        assert _union(line) == values(enum), name
    channel = re.search(r"channel\?: ([^}]+?) }", doc).group(1)
    assert _union(channel) == values(Channel)


def test_each_enum_value_is_its_own_string():
    assert Category.billing == "billing"
    assert isinstance(Channel.web, str)


def test_escalation_statuses_match_the_api_contract():
    from app.schemas.common import EscalationStatus

    assert [s.value for s in EscalationStatus] == ["open", "acknowledged", "resolved"]
