"""QA defect: the escalation-judgement model call was recorded with a hard-coded 0 ms.

Only the timing instrumentation changed. Each case also asserts the risk level and the escalation
outcome are exactly what they were before, so a timing fix cannot move a safety decision.
"""

import asyncio

import pytest

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

TICKETS = "/api/v1/tickets"
DELAY_S = 0.06  # long enough to measure, short enough to keep the suite fast


@pytest.fixture(autouse=True)
def _fresh_checkpoints(fresh_db):
    from app.services import workflow_service

    workflow_service.reset_checkpointer()
    yield
    workflow_service.reset_checkpointer()


def _slow_on_escalation_judgement(monkeypatch, *, then_fail: Exception | None = None):
    """Make only the EscalationDecision model call take DELAY_S, optionally ending in an error."""
    from app.core.llm import FakeProvider

    original = FakeProvider.complete

    async def complete(self, schema, messages, temperature, hints):
        if schema.__name__ == "EscalationDecision":
            await asyncio.sleep(DELAY_S)
            if then_fail is not None:
                raise then_fail
        return await original(self, schema, messages, temperature, hints)

    monkeypatch.setattr(FakeProvider, "complete", complete)


def _run(client, headers, number: str = "CD-1010"):
    page = client.get(TICKETS, headers=headers, params={"search": number}).json()
    ticket_id = next(t["id"] for t in page["items"] if t["ticket_number"] == number)
    assert client.post(f"{TICKETS}/{ticket_id}/run", headers=headers).status_code == 202
    state = client.get(f"{TICKETS}/{ticket_id}/workflow", headers=headers).json()
    events = client.get(f"{TICKETS}/{ticket_id}/events", headers=headers).json()
    return state, events


def _judgement_events(events):
    return [
        e
        for e in events
        if e["event_type"] == "llm_called" and e["message"] == "escalation judgement"
    ]


def test_a_successful_judgement_records_its_real_elapsed_time(client, agent_headers, monkeypatch):
    _slow_on_escalation_judgement(monkeypatch)
    state, events = _run(client, agent_headers)

    judgement = _judgement_events(events)
    assert len(judgement) == 1
    assert judgement[0]["duration_ms"] >= DELAY_S * 1000 * 0.8
    assert judgement[0]["node"] == "risk_check"
    # Safety outcome unchanged: a low-risk feature request completes with no escalation.
    assert state["risk"]["level"] == "low"
    assert state["escalation_required"] is False
    assert state["status"] == "completed"


def test_a_failing_judgement_still_records_the_time_it_took(client, agent_headers, monkeypatch):
    _slow_on_escalation_judgement(monkeypatch, then_fail=RuntimeError("provider down"))
    state, events = _run(client, agent_headers)

    judgement = _judgement_events(events)
    # A failed call spends no tokens, so no llm event exists; the node timing still covers it.
    node = next(
        e for e in events if e["event_type"] == "node_completed" and e["node"] == "risk_check"
    )
    assert node["duration_ms"] >= DELAY_S * 1000 * 0.8
    assert all(e["duration_ms"] >= 0 for e in judgement)
    # Safety fallback unchanged: the same decision the run reaches without the model's help.
    assert state["risk"]["level"] == "low"
    assert state["escalation_required"] is False


def test_a_timed_out_judgement_takes_the_same_failure_path(client, agent_headers, monkeypatch):
    _slow_on_escalation_judgement(monkeypatch, then_fail=TimeoutError("timed out"))
    state, events = _run(client, agent_headers)

    node = next(
        e for e in events if e["event_type"] == "node_completed" and e["node"] == "risk_check"
    )
    assert node["duration_ms"] >= DELAY_S * 1000 * 0.8
    assert state["risk"]["level"] == "low"
    assert state["escalation_required"] is False
    assert state["status"] == "completed"


def test_a_policy_escalation_makes_no_model_call_and_records_none(client, agent_headers):
    state, events = _run(client, agent_headers, "CD-1005")  # security: decided by rules

    assert _judgement_events(events) == []
    assert state["escalation_required"] is True
    assert state["status"] == "escalated"


def test_the_timing_is_a_monotonic_measure_not_a_constant():
    import inspect

    from agents.nodes import decision

    source = inspect.getsource(decision.risk_check)
    assert "tracer.llm(RISK, usage_dict(usage), 0," not in source
    assert "perf_counter" in source
