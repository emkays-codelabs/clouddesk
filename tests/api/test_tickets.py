"""P4-2 (F1): create, list and read tickets. Creating a ticket never starts a workflow."""

import asyncio

import pytest

from app.core.database import get_sessionmaker
from app.repositories.tickets import TicketRepository
from app.repositories.workflow import WorkflowRunRepository
from app.schemas.common import Severity

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

TICKETS = "/api/v1/tickets"
CHANNELS = ["email", "chat", "web", "api"]


def _customer_id(client, headers) -> str:
    found = client.get(TICKETS, headers=headers, params={"search": "CD-1001"}).json()
    return found["items"][0]["customer_id"]


def _create(client, headers, customer_id, **overrides):
    body = {
        "customer_id": customer_id,
        "subject": "Cannot sync",
        "body": "Sync stopped.",
        **overrides,
    }
    return client.post(TICKETS, headers=headers, json=body)


@pytest.mark.parametrize("channel", CHANNELS)
def test_each_channel_creates_a_ticket_and_its_first_message(client, agent_headers, channel):
    customer_id = _customer_id(client, agent_headers)

    response = _create(client, agent_headers, customer_id, channel=channel, body=f"via {channel}")

    assert response.status_code == 201
    ticket = response.json()
    assert ticket["channel"] == channel and ticket["status"] == "new"
    assert ticket["ticket_number"].startswith("CD-") and ticket["customer_id"] == customer_id
    assert ticket["customer_name"] and ticket["severity"] is None and ticket["tags"] == []
    detail = client.get(f"{TICKETS}/{ticket['id']}", headers=agent_headers).json()
    assert [(m["role"], m["body"]) for m in detail["messages"]] == [("customer", f"via {channel}")]
    assert detail["messages"][0]["author_name"] == ticket["customer_name"]


def test_channel_defaults_to_web(client, agent_headers):
    customer_id = _customer_id(client, agent_headers)
    body = {"customer_id": customer_id, "subject": "s", "body": "b"}
    assert client.post(TICKETS, headers=agent_headers, json=body).json()["channel"] == "web"


def test_ticket_numbers_continue_after_the_seed_and_never_repeat(client, agent_headers):
    customer_id = _customer_id(client, agent_headers)

    numbers = [
        _create(client, agent_headers, customer_id).json()["ticket_number"] for _ in range(3)
    ]

    values = [int(n.removeprefix("CD-")) for n in numbers]
    assert values[0] > 1013 and values[1] == values[0] + 1 and values[2] == values[1] + 1


def test_create_does_not_start_a_workflow(client, agent_headers):
    ticket = _create(client, agent_headers, _customer_id(client, agent_headers)).json()

    async def runs():
        async with get_sessionmaker()() as session:
            return await WorkflowRunRepository(session).latest_for_ticket(ticket["id"])

    assert asyncio.run(runs()) is None
    detail = client.get(f"{TICKETS}/{ticket['id']}", headers=agent_headers).json()
    assert detail["workflow"] is None and detail["status"] == "new"


def test_admin_can_create(client, admin_headers):
    customer_id = _customer_id(client, admin_headers)
    assert _create(client, admin_headers, customer_id).status_code == 201


def test_viewer_gets_403_on_create_and_nothing_is_written(client, viewer_headers, agent_headers):
    customer_id = _customer_id(client, agent_headers)
    before = client.get(TICKETS, headers=agent_headers).json()["total"]

    response = _create(client, viewer_headers, customer_id)

    assert response.status_code == 403
    assert client.get(TICKETS, headers=agent_headers).json()["total"] == before


def test_create_without_a_token_is_401(client):
    assert client.post(TICKETS, json={}).status_code == 401


def test_create_for_an_unknown_customer_is_404(client, agent_headers):
    assert _create(client, agent_headers, "no-such-customer").status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [{"channel": "fax"}, {"subject": ""}, {"subject": "x" * 301}, {"body": ""}, {"extra": 1}],
)
def test_invalid_create_bodies_are_422(client, agent_headers, overrides):
    customer_id = _customer_id(client, agent_headers)
    assert _create(client, agent_headers, customer_id, **overrides).status_code == 422


def test_seeded_tickets_cd_1001_to_cd_1013_are_fetchable(client, viewer_headers):
    numbers = set()
    for n in range(1001, 1014):
        number = f"CD-{n}"
        found = client.get(TICKETS, headers=viewer_headers, params={"search": number}).json()
        ticket_id = next(i["id"] for i in found["items"] if i["ticket_number"] == number)
        response = client.get(f"{TICKETS}/{ticket_id}", headers=viewer_headers)
        assert response.status_code == 200
        numbers.add(response.json()["ticket_number"])
    assert numbers == {f"CD-{n}" for n in range(1001, 1014)}


def test_get_returns_the_full_detail(client, viewer_headers):
    found = client.get(TICKETS, headers=viewer_headers, params={"search": "CD-1002"}).json()
    detail = client.get(f"{TICKETS}/{found['items'][0]['id']}", headers=viewer_headers).json()

    assert detail["subject"].startswith("Refund") and detail["body"]
    assert detail["customer"]["company"] == "BrightPath Studio"
    assert detail["customer_name"] == detail["customer"]["name"]
    assert detail["subscription"]["seats"] == 8
    assert detail["messages"][0]["role"] == "customer"
    assert detail["workflow"] is None and detail["escalation"] is None
    assert detail["resolution_actions"] == []
    assert all(h["id"] != detail["id"] for h in detail["history"])


def test_unknown_ticket_is_404_for_any_role(client, viewer_headers):
    response = client.get(f"{TICKETS}/does-not-exist", headers=viewer_headers)
    assert response.status_code == 404 and response.json() == {"detail": "Ticket not found"}


def test_get_and_list_require_a_token(client):
    assert client.get(f"{TICKETS}/x").status_code == 401
    assert client.get(TICKETS).status_code == 401


def test_list_returns_the_contract_shape_newest_first(client, viewer_headers):
    body = client.get(TICKETS, headers=viewer_headers).json()

    assert set(body) == {"items", "total", "page", "page_size"}
    assert body["page"] == 1 and body["page_size"] == 20 and body["total"] >= 13
    assert set(body["items"][0]) == {
        "id", "ticket_number", "subject", "status", "severity", "category", "customer_id",
        "customer_name", "channel", "created_at", "updated_at", "escalation_required",
        "approval_status",
    }  # fmt: skip
    stamps = [i["created_at"] for i in body["items"]]
    assert stamps == sorted(stamps, reverse=True)


def test_list_filters_by_severity_status_and_search(client, viewer_headers, agent_headers):
    customer_id = _customer_id(client, agent_headers)
    marker = _create(client, agent_headers, customer_id, subject="Zebra crossing zq9").json()

    by_search = client.get(TICKETS, headers=viewer_headers, params={"search": "zq9"}).json()
    assert [i["id"] for i in by_search["items"]] == [marker["id"]]
    by_number = client.get(TICKETS, headers=viewer_headers, params={"search": "cd-1005"}).json()
    assert [i["ticket_number"] for i in by_number["items"]] == ["CD-1005"]

    new = client.get(TICKETS, headers=viewer_headers, params={"status": "new", "page_size": 100})
    assert marker["id"] in {i["id"] for i in new.json()["items"]}
    assert {i["status"] for i in new.json()["items"]} == {"new"}

    async def raise_severity():  # the seed carries no severity, so set one the way a run would
        async with get_sessionmaker()() as session:
            await TicketRepository(session).update(marker["id"], severity=Severity.critical)
            await session.commit()

    asyncio.run(raise_severity())
    critical = client.get(TICKETS, headers=viewer_headers, params={"severity": "critical"}).json()
    assert marker["id"] in {i["id"] for i in critical["items"]}
    assert {i["severity"] for i in critical["items"]} == {"critical"}
    both = client.get(
        TICKETS, headers=viewer_headers, params={"severity": "critical", "status": "closed"}
    ).json()
    assert both["total"] == 0 and both["items"] == []


def test_list_pages_without_overlap(client, viewer_headers):
    first = client.get(TICKETS, headers=viewer_headers, params={"page_size": 5}).json()
    second = client.get(TICKETS, headers=viewer_headers, params={"page_size": 5, "page": 2}).json()

    assert len(first["items"]) == 5 and second["page"] == 2 and second["page_size"] == 5
    assert first["total"] == second["total"]
    assert not {i["id"] for i in first["items"]} & {i["id"] for i in second["items"]}
    last = client.get(TICKETS, headers=viewer_headers, params={"page": 999}).json()
    assert last["items"] == [] and last["total"] == first["total"]


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 0}, {"page_size": 101}, {"status": "bogus"}, {"severity": "p1"}],
)
def test_list_rejects_bad_query_values_with_422(client, viewer_headers, params):
    assert client.get(TICKETS, headers=viewer_headers, params=params).status_code == 422
