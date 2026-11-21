"""P4-4 (F12): reply, request-info, escalate and update. Nothing is sent; everything is stored."""

import pytest

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

TICKETS = "/api/v1/tickets"
ACTIONS = [
    ("post", "/reply", {"body": "x"}),
    ("post", "/request-info", {"questions": ["q"]}),
    ("post", "/escalate", {"reason": "r"}),
    ("patch", "", {"status": "closed"}),
]


def _ticket(client, headers, number="CD-1001") -> dict:
    # A fresh ticket per test: the demo database is shared, so seeded rows must stay untouched.
    customer_id = client.get(TICKETS, headers=headers, params={"search": number}).json()["items"][
        0
    ]["customer_id"]
    body = {"customer_id": customer_id, "subject": "Action test", "body": "Help."}
    return client.post(TICKETS, headers=headers, json=body).json()


def _detail(client, headers, ticket_id) -> dict:
    return client.get(f"{TICKETS}/{ticket_id}", headers=headers).json()


def test_reply_is_stored_as_an_agent_message(client, agent_headers):
    t = _ticket(client, agent_headers)
    r = client.post(f"{TICKETS}/{t['id']}/reply", headers=agent_headers, json={"body": "Fixed."})
    assert r.status_code == 201
    msg = r.json()
    assert msg["role"] == "agent" and msg["body"] == "Fixed." and msg["internal"] is False
    assert msg["author_name"] == "sam.agent@clouddesk.demo"
    assert _detail(client, agent_headers, t["id"])["messages"][-1]["id"] == msg["id"]


def test_reply_internal_flag_is_respected(client, agent_headers):
    t = _ticket(client, agent_headers)
    url = f"{TICKETS}/{t['id']}/reply"
    r = client.post(url, headers=agent_headers, json={"body": "note", "internal": True})
    assert r.json()["internal"] is True


def test_reply_rejects_empty_body(client, agent_headers):
    t = _ticket(client, agent_headers)
    url = f"{TICKETS}/{t['id']}/reply"
    assert client.post(url, headers=agent_headers, json={"body": ""}).status_code == 422


def test_request_info_sets_waiting_and_records_the_transition(client, agent_headers):
    t = _ticket(client, agent_headers)
    r = client.post(
        f"{TICKETS}/{t['id']}/request-info",
        headers=agent_headers,
        json={"questions": ["Which IdP?", "Since when?"]},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "agent" and "1. Which IdP?" in r.json()["body"]
    assert "2. Since when?" in r.json()["body"]
    detail = _detail(client, agent_headers, t["id"])
    assert detail["status"] == "waiting_on_customer"
    last = detail["messages"][-1]
    assert last["role"] == "system" and last["internal"] is True
    assert f"from {t['status']} to waiting_on_customer" in last["body"]


def test_request_info_needs_a_question(client, agent_headers):
    t = _ticket(client, agent_headers)
    url = f"{TICKETS}/{t['id']}/request-info"
    assert client.post(url, headers=agent_headers, json={"questions": []}).status_code == 422


def test_escalate_writes_a_human_escalation_and_sets_status(client, agent_headers):
    t = _ticket(client, agent_headers, "CD-1002")
    r = client.post(
        f"{TICKETS}/{t['id']}/escalate",
        headers=agent_headers,
        json={"reason": "Customer threatens churn", "priority": "urgent"},
    )
    assert r.status_code == 201
    esc = r.json()
    assert esc["created_by"] == "human" and esc["priority"] == "urgent"
    assert (
        esc["status"] == "open"
        and esc["assigned_team"]
        and esc["ticket_number"] == t["ticket_number"]
    )
    detail = _detail(client, agent_headers, t["id"])
    assert detail["status"] == "escalated" and detail["escalation_required"] is True
    assert detail["escalation"]["id"] == esc["id"]
    assert "to escalated" in detail["messages"][-1]["body"]


def test_escalate_priority_defaults_to_normal_and_rejects_unknown(client, agent_headers):
    t = _ticket(client, agent_headers)
    url = f"{TICKETS}/{t['id']}/escalate"
    default = client.post(url, headers=agent_headers, json={"reason": "x"})
    assert default.json()["priority"] == "normal"
    bad = client.post(url, headers=agent_headers, json={"reason": "x", "priority": "p1"})
    assert bad.status_code == 422


def test_patch_updates_fields_and_leaves_the_rest(client, agent_headers):
    t = _ticket(client, agent_headers)
    r = client.patch(
        f"{TICKETS}/{t['id']}",
        headers=agent_headers,
        json={"severity": "high", "assigned_to": "sam"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["severity"] == "high" and body["assigned_to"] == "sam"
    assert body["status"] == t["status"] and body["customer_name"]
    assert len(_detail(client, agent_headers, t["id"])["messages"]) == 1  # no status change


def test_patch_status_records_transition_and_resolved_at(client, agent_headers):
    t = _ticket(client, agent_headers)
    url = f"{TICKETS}/{t['id']}"
    r = client.patch(url, headers=agent_headers, json={"status": "resolved"})
    assert r.json()["status"] == "resolved" and r.json()["resolved_at"] is not None
    last = _detail(client, agent_headers, t["id"])["messages"][-1]
    assert last["role"] == "system" and "to resolved by sam.agent@clouddesk.demo" in last["body"]
    reopened = client.patch(url, headers=agent_headers, json={"status": "in_progress"})
    assert reopened.json()["resolved_at"] is None


def test_patch_can_unassign_and_rejects_bad_values(client, agent_headers):
    t = _ticket(client, agent_headers)
    url = f"{TICKETS}/{t['id']}"
    client.patch(url, headers=agent_headers, json={"assigned_to": "sam"})
    unassigned = client.patch(url, headers=agent_headers, json={"assigned_to": None})
    assert unassigned.json()["assigned_to"] is None
    assert client.patch(url, headers=agent_headers, json={"status": "bogus"}).status_code == 422


def test_admin_can_act(client, admin_headers):
    t = _ticket(client, admin_headers)
    r = client.post(f"{TICKETS}/{t['id']}/reply", headers=admin_headers, json={"body": "hi"})
    assert r.status_code == 201


@pytest.mark.parametrize(("method", "suffix", "body"), ACTIONS)
def test_viewer_gets_403_and_nothing_changes(
    client, viewer_headers, agent_headers, method, suffix, body
):
    t = _ticket(client, agent_headers)
    r = client.request(method, f"{TICKETS}/{t['id']}{suffix}", headers=viewer_headers, json=body)
    assert r.status_code == 403
    after = _detail(client, agent_headers, t["id"])
    assert after["status"] == t["status"] and len(after["messages"]) == 1
    assert after["escalation"] is None


@pytest.mark.parametrize(("method", "suffix", "body"), ACTIONS)
def test_unknown_ticket_is_404_and_no_token_is_401(client, agent_headers, method, suffix, body):
    url = f"{TICKETS}/no-such{suffix}"
    assert client.request(method, url, headers=agent_headers, json=body).status_code == 404
    assert client.request(method, url, json=body).status_code == 401
