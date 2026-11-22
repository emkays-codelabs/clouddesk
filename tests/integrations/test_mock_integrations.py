"""P6-4: mock integrations record calls and never reach a real system (no real email or refunds)."""

import ast
from pathlib import Path

import pytest

from integrations.factory import IntegrationsNotAvailable, get_integrations, reset_integrations
from integrations.mock.services import (
    MockBillingService,
    MockEmailSender,
    MockTicketNotifier,
    MockWorkspaceAdmin,
)
from integrations.protocols import BillingService, EmailSender, TicketNotifier, WorkspaceAdmin

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _reset():
    reset_integrations()
    yield
    reset_integrations()


def test_factory_returns_mocks_in_demo_mode():
    bundle = get_integrations(demo_mode=True)
    assert isinstance(bundle.email, MockEmailSender)
    assert isinstance(bundle.billing, MockBillingService)
    assert isinstance(bundle.workspace_admin, MockWorkspaceAdmin)
    assert isinstance(bundle.notifier, MockTicketNotifier)


def test_factory_returns_one_shared_bundle_so_calls_stay_inspectable():
    assert get_integrations(demo_mode=True) is get_integrations(demo_mode=True)


def test_factory_refuses_outside_demo_mode_because_v1_has_no_real_adapter():
    with pytest.raises(IntegrationsNotAvailable):
        get_integrations(demo_mode=False)


def test_mocks_satisfy_the_protocols():
    bundle = get_integrations(demo_mode=True)
    assert isinstance(bundle.email, EmailSender)
    assert isinstance(bundle.billing, BillingService)
    assert isinstance(bundle.workspace_admin, WorkspaceAdmin)
    assert isinstance(bundle.notifier, TicketNotifier)


async def test_email_is_recorded_not_sent():
    mail = MockEmailSender()
    out = await mail.send("a@example.com", "Hi", "Body")
    assert out["status"] == "recorded"
    assert [c.method for c in mail.calls] == ["send"]
    assert mail.calls[0].args["to"] == "a@example.com"


async def test_refund_is_recorded_and_can_be_read_back():
    billing = MockBillingService()
    refund = await billing.create_refund("c1", "s1", 24.0, "overbilled", "key-1")
    assert refund["status"] == "recorded" and refund["amount"] == 24.0
    assert (await billing.get_refund(refund["id"]))["amount"] == 24.0
    assert await billing.get_refund("missing") is None
    assert len(billing.calls) == 1


async def test_billing_refund_is_idempotent_on_its_key():
    billing = MockBillingService()
    a = await billing.create_refund("c1", "s1", 24.0, "r", "key-1")
    b = await billing.create_refund("c1", "s1", 24.0, "r", "key-1")
    assert a["id"] == b["id"]
    assert len(billing.refunds) == 1


async def test_workspace_reset_is_recorded_and_readable():
    admin = MockWorkspaceAdmin()
    out = await admin.reset_setting("w1", "sso")
    assert out["status"] == "recorded"
    assert await admin.get_setting_state("w1", "sso") == "reset"
    assert await admin.get_setting_state("w1", "other") is None


async def test_notifier_records():
    notifier = MockTicketNotifier()
    await notifier.notify("t1", "hello")
    assert notifier.calls[0].args == {"ticket_id": "t1", "message": "hello"}


def test_core_never_imports_integrations():
    core = ROOT / "backend" / "app" / "core"
    files = sorted(core.rglob("*.py"))
    assert files
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] != "integrations", f"{path.name} imports {name}"
