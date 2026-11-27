"""P10-5, P11-1..P11-4 (F9, F10, F11, F13, N4): the workflow runs, pauses, resumes and escalates.

Each test drives the real app through its API on a private database, with the fake LLM:
`POST /tickets/{id}/run` returns 202, the background run finishes, and the state, events, approvals
and escalations are read back through the same API a person would use.
"""

import pytest

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

TICKETS = "/api/v1/tickets"


@pytest.fixture(autouse=True)
def _fresh_checkpoints(fresh_db):
    from app.services import workflow_service

    workflow_service.reset_checkpointer()
    yield
    workflow_service.reset_checkpointer()


def _ticket_id(client, headers, number: str) -> str:
    page = client.get(TICKETS, headers=headers, params={"search": number}).json()
    return next(t["id"] for t in page["items"] if t["ticket_number"] == number)


def _run(client, headers, number: str) -> tuple[str, dict]:
    ticket_id = _ticket_id(client, headers, number)
    response = client.post(f"{TICKETS}/{ticket_id}/run", headers=headers)
    assert response.status_code == 202, response.text
    state = client.get(f"{TICKETS}/{ticket_id}/workflow", headers=headers).json()
    return ticket_id, state


def test_a_low_risk_ticket_runs_to_the_end_and_remembers(client, agent_headers):
    ticket_id, state = _run(client, agent_headers, "CD-1010")

    assert state["status"] == "completed"
    assert state["completed_nodes"][-3:] == [
        "execute_resolution",
        "ticket_summary",
        "memory_update",
    ]
    assert state["risk"]["level"] == "low"
    assert state["severity"] == "low"
    assert state["escalation_required"] is False
    assert state["final_response"] and state["ticket_summary"]
    events = client.get(f"{TICKETS}/{ticket_id}/events", headers=agent_headers).json()
    kinds = {e["event_type"] for e in events}
    assert {"node_started", "node_completed", "workflow_completed"} <= kinds
    assert any(e["duration_ms"] is not None for e in events if e["event_type"] == "node_completed")


def test_a_refund_pauses_for_approval_then_runs_once_when_approved(client, agent_headers):
    ticket_id, state = _run(client, agent_headers, "CD-1002")

    assert state["status"] == "waiting_for_approval"
    assert state["approval_status"] == "pending"
    ticket = client.get(f"{TICKETS}/{ticket_id}", headers=agent_headers).json()
    assert ticket["status"] == "waiting_on_approval"
    pending = client.get("/api/v1/approvals", headers=agent_headers, params={"status": "pending"})
    approval = next(a for a in pending.json() if a["ticket_id"] == ticket_id)
    assert approval["action"]["tool"] == "create_refund_request"
    assert approval["action"]["requires_approval"] is True

    # A second run while the ticket waits is a conflict, not a second pause.
    assert client.post(f"{TICKETS}/{ticket_id}/run", headers=agent_headers).status_code == 409

    done = client.post(
        f"/api/v1/approvals/{approval['id']}/approve", headers=agent_headers, json={"note": "ok"}
    )
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["approval"]["status"] == "approved"
    assert body["workflow"]["status"] == "completed"
    detail = client.get(f"{TICKETS}/{ticket_id}", headers=agent_headers).json()
    refunds = [a for a in detail["resolution_actions"] if a["tool"] == "create_refund_request"]
    assert len(refunds) == 1 and refunds[0]["status"] == "executed"

    # Deciding again is a conflict (the run is no longer paused), and nothing is refunded twice.
    again = client.post(
        f"/api/v1/approvals/{approval['id']}/approve", headers=agent_headers, json={}
    )
    assert again.status_code == 409
    detail = client.get(f"{TICKETS}/{ticket_id}", headers=agent_headers).json()
    assert (
        len([a for a in detail["resolution_actions"] if a["tool"] == "create_refund_request"]) == 1
    )


def test_a_rejected_refund_escalates_and_never_executes(client, agent_headers):
    ticket_id, _ = _run(client, agent_headers, "CD-1002")
    pending = client.get("/api/v1/approvals", headers=agent_headers, params={"status": "pending"})
    approval = next(a for a in pending.json() if a["ticket_id"] == ticket_id)

    done = client.post(f"/api/v1/approvals/{approval['id']}/reject", headers=agent_headers, json={})

    assert done.status_code == 200, done.text
    assert done.json()["workflow"]["status"] == "escalated"
    detail = client.get(f"{TICKETS}/{ticket_id}", headers=agent_headers).json()
    assert detail["status"] == "escalated"
    assert detail["escalation"] is not None
    executed = [a for a in detail["resolution_actions"] if a["status"] == "executed"]
    assert not [a for a in executed if a["tool"] == "create_refund_request"]


@pytest.mark.parametrize("number", ["CD-1005", "CD-1006", "CD-1009", "CD-1011"])
def test_policy_cases_escalate_without_an_approval_wait(client, agent_headers, number):
    ticket_id, state = _run(client, agent_headers, number)

    assert state["status"] == "escalated"
    assert state["escalation_required"] is True
    assert "human_approval" not in state["completed_nodes"]
    detail = client.get(f"{TICKETS}/{ticket_id}", headers=agent_headers).json()
    assert detail["status"] == "escalated"
    assert detail["escalation"]["assigned_team"]


def test_an_injection_ticket_stays_data_and_exports_nothing(client, agent_headers):
    ticket_id, state = _run(client, agent_headers, "CD-1013")

    assert state["status"] == "escalated"
    assert state["risk"]["level"] == "high"
    tools = {a.get("tool") for a in state.get("actions", [])}
    assert not any("export" in (t or "") for t in tools)
    assert not [a for a in state.get("actions", []) if a["status"] == "executed"]


def test_a_viewer_cannot_run_or_approve(client, agent_headers, viewer_headers):
    ticket_id = _ticket_id(client, agent_headers, "CD-1010")

    assert client.post(f"{TICKETS}/{ticket_id}/run", headers=viewer_headers).status_code == 403
    assert (
        client.post("/api/v1/approvals/x/approve", headers=viewer_headers, json={}).status_code
        == 403
    )


def test_run_and_workflow_routes_404_for_an_unknown_ticket(client, agent_headers):
    assert client.post(f"{TICKETS}/nope/run", headers=agent_headers).status_code == 404
    assert client.get(f"{TICKETS}/nope/workflow", headers=agent_headers).status_code == 404
    assert client.get(f"{TICKETS}/nope/events", headers=agent_headers).status_code == 404


def test_the_agents_overview_lists_six_agents_and_the_graph(client, agent_headers):
    _run(client, agent_headers, "CD-1010")

    body = client.get("/api/v1/agents", headers=agent_headers).json()

    assert len(body["agents"]) == 6
    assert len(body["graph"]["nodes"]) == 12
    assert body["stats"]["runs_total"] >= 1
    assert body["recent_runs"]


def test_escalations_can_be_listed_and_updated(client, agent_headers, viewer_headers):
    ticket_id, _ = _run(client, agent_headers, "CD-1005")

    listed = client.get("/api/v1/escalations", headers=viewer_headers).json()
    mine = next(e for e in listed if e["ticket_id"] == ticket_id)
    assert mine["status"] == "open"
    patched = client.patch(
        f"/api/v1/escalations/{mine['id']}",
        headers=agent_headers,
        json={"status": "acknowledged", "note": "taking it"},
    )
    assert patched.status_code == 200 and patched.json()["status"] == "acknowledged"
    forbidden = client.patch(
        f"/api/v1/escalations/{mine['id']}", headers=viewer_headers, json={"status": "resolved"}
    )
    assert forbidden.status_code == 403


def test_a_second_run_while_one_is_running_is_a_conflict(client, agent_headers, monkeypatch):
    """A run that has started and not finished blocks another: no two runs race on a ticket."""
    from app.services import workflow_service

    async def never_finishes(run_id: str) -> None:
        return None

    monkeypatch.setattr(workflow_service, "start_workflow", never_finishes)
    ticket_id = _ticket_id(client, agent_headers, "CD-1010")

    first = client.post(f"{TICKETS}/{ticket_id}/run", headers=agent_headers)
    second = client.post(f"{TICKETS}/{ticket_id}/run", headers=agent_headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert "in progress" in second.json()["detail"]
