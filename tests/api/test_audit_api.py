"""P4-5 (N6): GET /audit pages and filters the audit log; any authenticated role may read."""

import pytest

pytestmark = [
    pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning"),
    pytest.mark.usefixtures("fresh_db"),
]

AUDIT = "/api/v1/audit"
ESCALATE = "POST /api/v1/tickets/nope/escalate"
ROW_KEYS = {
    "id",
    "actor",
    "actor_type",
    "action",
    "resource_type",
    "resource_id",
    "details",
    "request_id",
    "created_at",
}


def _make_rows(client, agent_headers, admin_headers) -> None:
    client.post("/api/v1/tickets/nope/reply", headers=agent_headers, json={"body": "x"})
    client.post("/api/v1/tickets/nope/escalate", headers=agent_headers, json={"reason": "r"})
    client.post("/api/v1/tickets/nope/reply", headers=admin_headers, json={"body": "x"})


def test_unauthenticated_gets_401(client):
    assert client.get(AUDIT).status_code == 401


def test_viewer_can_read_and_rows_match_the_contract(
    client, viewer_headers, agent_headers, admin_headers
):
    _make_rows(client, agent_headers, admin_headers)

    response = client.get(AUDIT, headers=viewer_headers)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total"}
    assert body["total"] == 3
    assert set(body["items"][0]) == ROW_KEYS
    assert body["items"][0]["actor"] == "admin@clouddesk.demo"  # newest first
    assert body["items"][0]["details"]["status_code"] == 404


def test_filters_by_actor_and_action_and_pages(
    client, viewer_headers, agent_headers, admin_headers
):
    _make_rows(client, agent_headers, admin_headers)
    sam = "sam.agent@clouddesk.demo"

    by_actor = client.get(AUDIT, headers=viewer_headers, params={"actor": sam})
    assert by_actor.json()["total"] == 2

    by_action = client.get(AUDIT, headers=viewer_headers, params={"action": ESCALATE})
    assert by_action.json()["total"] == 1

    both = client.get(
        AUDIT,
        headers=viewer_headers,
        params={"actor": "admin@clouddesk.demo", "action": ESCALATE},
    )
    assert both.json() == {"items": [], "total": 0}

    page = client.get(AUDIT, headers=viewer_headers, params={"page": 2, "page_size": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 1


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_bad_paging_is_422(client, viewer_headers, params):
    assert client.get(AUDIT, headers=viewer_headers, params=params).status_code == 422
