"""P11-5 (F9, F10, F14): `make demo` pauses CD-1002 for approval and escalates CD-1005 by policy."""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "demo.py"


@pytest.fixture(autouse=True)
def _fresh(fresh_db):
    from app.services import workflow_service

    workflow_service.reset_checkpointer()
    yield
    workflow_service.reset_checkpointer()


def _demo():
    spec = importlib.util.spec_from_file_location("clouddesk_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["clouddesk_demo"] = module
    spec.loader.exec_module(module)
    return module


def test_cd_1002_pauses_for_approval_and_records_the_refund_once_when_approved():
    lines: list[str] = []

    state = _demo().run("CD-1002", decide=lambda: "approve", out=lines.append)

    text = "\n".join(lines)
    assert "Waiting for you" in text
    assert "create_refund_request" in text
    assert state["status"] == "completed"
    assert text.count("Action create_refund_request: executed") == 1


def test_cd_1002_rejected_escalates_instead():
    lines: list[str] = []

    state = _demo().run("CD-1002", decide=lambda: "reject", out=lines.append)

    assert state["status"] == "escalated"
    assert "Ticket status: escalated" in "\n".join(lines)


def test_cd_1005_escalates_by_policy_with_no_approval_question():
    lines: list[str] = []

    def never() -> str:
        raise AssertionError("a policy escalation must not ask for an approval")

    state = _demo().run("CD-1005", decide=never, out=lines.append)

    assert state["status"] == "escalated"
    assert "Escalated to:" in "\n".join(lines)


def test_an_unknown_ticket_says_so_and_returns_nothing():
    lines: list[str] = []

    assert _demo().run("CD-9999", decide=lambda: "approve", out=lines.append) == {}
    assert "No ticket CD-9999" in lines[0]


def test_the_demo_uses_the_offline_model_unless_asked(monkeypatch):
    monkeypatch.delenv("DEMO_REAL_LLM", raising=False)
    monkeypatch.setenv("TICKET", "CD-1010")
    module = _demo()

    assert module.main() == 0

    import os

    assert os.environ["LLM_PROVIDER"] == "fake"
