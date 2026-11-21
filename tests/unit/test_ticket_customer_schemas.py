"""P4-1: ticket and customer schemas serialize to the shapes in docs/design/06_API_CONTRACT.md."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas import common
from app.schemas.customer import Customer, CustomerDetail, CustomerMemory, Subscription, Workspace
from app.schemas.ticket import (
    Ticket,
    TicketCreate,
    TicketEscalate,
    TicketMessage,
    TicketPage,
    TicketReply,
    TicketRequestInfo,
    TicketSummary,
    TicketUpdate,
)
from app.schemas.ticket_detail import TicketDetail
from app.schemas.workflow import Escalation, ResolutionAction

NOW = datetime(2026, 11, 22, tzinfo=UTC)

SUMMARY = {
    "id": "t1",
    "ticket_number": "CD-1001",
    "subject": "s",
    "status": "new",
    "severity": None,
    "category": None,
    "customer_id": "c1",
    "customer_name": "Priya",
    "channel": "email",
    "created_at": NOW,
    "updated_at": NOW,
    "escalation_required": False,
    "approval_status": "not_required",
}
CUSTOMER = {
    "id": "c1",
    "name": "Priya",
    "email": "p@x.example",
    "company": "N",
    "plan_name": "enterprise",
    "status": "active",
    "created_at": NOW,
    "region": "eu-west",
    "lifetime_value": 1.0,
}
SUBSCRIPTION = {
    "id": "s1",
    "customer_id": "c1",
    "plan": "pro",
    "seats": 5,
    "status": "active",
    "renews_at": None,
    "mrr": 10.0,
    "storage_quota_gb": 100.0,
    "storage_used_gb": 1.0,
    "api_rate_limit": 100,
}


def fields(model) -> set[str]:
    return set(model.model_fields)


def test_ticket_summary_fields_match_contract():
    assert fields(TicketSummary) == {
        "id", "ticket_number", "subject", "status", "severity", "category", "customer_id",
        "customer_name", "channel", "created_at", "updated_at", "escalation_required",
        "approval_status",
    }  # fmt: skip


def test_ticket_adds_body_assignee_resolved_tags():
    assert fields(Ticket) - fields(TicketSummary) == {"body", "assigned_to", "resolved_at", "tags"}


def test_ticket_message_fields_match_contract():
    assert fields(TicketMessage) == {
        "id", "ticket_id", "role", "author_name", "body", "internal", "attachments", "created_at",
    }  # fmt: skip


def test_ticket_detail_extends_ticket_with_contract_fields():
    assert fields(TicketDetail) - fields(Ticket) == {
        "messages", "customer", "subscription", "history", "workflow", "resolution_actions",
        "escalation",
    }  # fmt: skip


def test_customer_and_detail_fields_match_contract():
    assert fields(Customer) == {
        "id", "name", "email", "company", "plan_name", "status", "created_at", "region",
        "lifetime_value",
    }  # fmt: skip
    assert fields(CustomerDetail) - fields(Customer) == {
        "subscription", "workspace", "tickets", "memory",
    }  # fmt: skip


def test_supporting_types_fields():
    assert "confidence" in fields(CustomerMemory)
    assert fields(Workspace) >= {"integrations", "sso_enabled", "member_count"}
    assert fields(Subscription) >= {"plan", "seats", "storage_quota_gb", "api_rate_limit"}
    assert fields(Escalation) >= {"ticket_number", "assigned_team", "created_by"}
    assert fields(ResolutionAction) >= {"tool", "arguments", "requires_approval", "executed_at"}


def test_summary_serializes_to_json_with_nullable_severity_and_category():
    data = TicketSummary(**SUMMARY).model_dump(mode="json")
    assert data["severity"] is None and data["category"] is None
    assert data["created_at"].startswith("2026-11-22")
    assert data["status"] == "new" and data["approval_status"] == "not_required"


def test_ticket_detail_round_trip_json():
    detail = TicketDetail(
        **SUMMARY,
        body="b",
        tags=["a"],
        messages=[
            {
                "id": "m1",
                "ticket_id": "t1",
                "role": "customer",
                "author_name": "P",
                "body": "hi",
                "internal": False,
                "attachments": [{"name": "a", "url": "u", "size": 3}],
                "created_at": NOW,
            }
        ],  # fmt: skip
        customer=CUSTOMER,
        subscription=SUBSCRIPTION,
        history=[SUMMARY],
        workflow={"workflow_id": "w", "ticket_id": "t1", "status": "running", "extra_key": 1},
    )
    data = detail.model_dump(mode="json")
    assert data["messages"][0]["attachments"][0] == {"name": "a", "url": "u", "size": 3}
    assert data["workflow"]["status"] == "running" and data["workflow"]["extra_key"] == 1
    assert data["escalation"] is None and data["resolution_actions"] == []
    assert data["customer"]["status"] == "active"


def test_customer_detail_nests_ticket_summaries():
    data = CustomerDetail(**CUSTOMER, subscription=SUBSCRIPTION, tickets=[SUMMARY]).model_dump(
        mode="json"
    )
    assert data["tickets"][0]["ticket_number"] == "CD-1001"
    assert data["workspace"] is None and data["memory"] == []


def test_page_shape():
    page = TicketPage(items=[SUMMARY], total=1, page=1, page_size=20).model_dump()
    assert set(page) == {"items", "total", "page", "page_size"}


def test_enums_come_from_common():
    assert TicketSummary.model_fields["status"].annotation is common.TicketStatus
    assert TicketSummary.model_fields["channel"].annotation is common.Channel
    assert TicketSummary.model_fields["approval_status"].annotation is common.ApprovalStatus
    assert TicketMessage.model_fields["role"].annotation is common.MessageRole
    assert Customer.model_fields["status"].annotation is common.CustomerStatus
    assert Subscription.model_fields["plan"].annotation is common.Plan
    assert CustomerMemory.model_fields["memory_type"].annotation is common.MemoryType
    assert [m.value for m in common.Plan] == ["free", "pro", "business", "enterprise"]
    assert [m.value for m in common.CustomerStatus] == ["active", "trial", "past_due", "churned"]


def test_invalid_enum_values_rejected():
    with pytest.raises(ValidationError):
        TicketSummary(**{**SUMMARY, "status": "open"})
    with pytest.raises(ValidationError):
        TicketSummary(**{**SUMMARY, "channel": "sms"})
    with pytest.raises(ValidationError):
        Customer(**{**CUSTOMER, "status": "gone"})


def test_ticket_create_defaults_and_validation():
    assert TicketCreate(customer_id="c", subject="s", body="b").channel == common.Channel.web
    for ch in ("email", "chat", "web", "api"):
        assert TicketCreate(customer_id="c", subject="s", body="b", channel=ch).channel == ch
    with pytest.raises(ValidationError):
        TicketCreate(customer_id="c", subject="", body="b")
    with pytest.raises(ValidationError):
        TicketCreate(customer_id="c", subject="s", body="b", channel="sms")
    with pytest.raises(ValidationError):
        TicketCreate(customer_id="c", subject="s", body="b", status="resolved")


def test_action_bodies():
    assert TicketReply(body="x").internal is False
    with pytest.raises(ValidationError):
        TicketReply(body="")
    with pytest.raises(ValidationError):
        TicketRequestInfo(questions=[])
    assert TicketEscalate(reason="r").priority == "normal"
    with pytest.raises(ValidationError):
        TicketEscalate(reason="r", priority="p0")
    assert TicketUpdate().model_dump(exclude_none=True) == {}
    assert TicketUpdate(status="resolved").status == common.TicketStatus.resolved
    with pytest.raises(ValidationError):
        TicketUpdate(severity="urgent")
