"""P4-6 (F1, upstream FR-31): the inbox filters by channel, assignee and AI state."""

import pytest

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

TICKETS = "/api/v1/tickets"


def _customer_id(client, headers) -> str:
    return client.get(TICKETS, headers=headers, params={"search": "CD-1001"}).json()["items"][0][
        "customer_id"
    ]


def _create(client, headers, channel: str, subject: str) -> dict:
    body = {
        "customer_id": _customer_id(client, headers),
        "subject": subject,
        "body": "Details",
        "channel": channel,
    }
    response = client.post(TICKETS, headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_the_channel_filter_returns_only_that_channel(client, agent_headers):
    made = _create(client, agent_headers, "chat", "Filter by chat channel")

    items = client.get(TICKETS, headers=agent_headers, params={"channel": "chat"}).json()["items"]

    assert made["id"] in {t["id"] for t in items}
    assert {t["channel"] for t in items} == {"chat"}


def test_an_unknown_channel_is_rejected(client, agent_headers):
    assert client.get(TICKETS, headers=agent_headers, params={"channel": "fax"}).status_code == 422


def test_the_assignee_filter_follows_an_update(client, agent_headers):
    made = _create(client, agent_headers, "web", "Assign me")
    client.patch(f"{TICKETS}/{made['id']}", headers=agent_headers, json={"assigned_to": "sam"})

    items = client.get(TICKETS, headers=agent_headers, params={"assigned_to": "sam"}).json()[
        "items"
    ]

    assert made["id"] in {t["id"] for t in items}
    assert all(t["id"] for t in items)
    other = client.get(TICKETS, headers=agent_headers, params={"assigned_to": "nobody"}).json()
    assert other["items"] == []


def test_the_ai_state_filters_find_escalated_tickets(client, agent_headers):
    made = _create(client, agent_headers, "email", "Escalate me")
    client.post(
        f"{TICKETS}/{made['id']}/escalate", headers=agent_headers, json={"reason": "needs a human"}
    )

    escalated = client.get(TICKETS, headers=agent_headers, params={"escalated": "true"}).json()
    calm = client.get(TICKETS, headers=agent_headers, params={"escalated": "false"}).json()

    assert made["id"] in {t["id"] for t in escalated["items"]}
    assert made["id"] not in {t["id"] for t in calm["items"]}


def test_the_approval_state_filter_accepts_a_known_value_only(client, agent_headers):
    ok = client.get(TICKETS, headers=agent_headers, params={"approval_status": "pending"})
    bad = client.get(TICKETS, headers=agent_headers, params={"approval_status": "maybe"})

    assert ok.status_code == 200
    assert bad.status_code == 422
