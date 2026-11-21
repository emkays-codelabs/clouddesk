"""P4-3 (F4): list and read customers with their subscription, workspace, tickets and memory."""

import asyncio

import pytest

from app.core.database import get_sessionmaker
from app.repositories.memory import CustomerMemoryRepository
from app.schemas.common import MemoryType

pytestmark = pytest.mark.filterwarnings("ignore:The HMAC key:UserWarning")

CUSTOMERS = "/api/v1/customers"


def _customer_id(client, headers, name="Priya Raman") -> str:
    found = client.get(CUSTOMERS, headers=headers, params={"search": name}).json()
    return found["items"][0]["id"]


def _seed_note(customer_id: str, content: str) -> None:
    async def add():
        async with get_sessionmaker()() as session:
            await CustomerMemoryRepository(session).add(
                customer_id=customer_id,
                memory_type=MemoryType.preference,
                content=content,
                confidence=0.9,
            )
            await session.commit()

    asyncio.run(add())


def test_unauthenticated_requests_get_401(client):
    assert client.get(CUSTOMERS).status_code == 401
    assert client.get(f"{CUSTOMERS}/anything").status_code == 401


def test_every_role_can_list(client, viewer_headers, agent_headers, admin_headers):
    for headers in (viewer_headers, agent_headers, admin_headers):
        response = client.get(CUSTOMERS, headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 8


def test_detail_loads_subscription_workspace_tickets_and_memory(client, viewer_headers):
    customer_id = _customer_id(client, viewer_headers)
    _seed_note(customer_id, "Prefers email over chat")

    response = client.get(f"{CUSTOMERS}/{customer_id}", headers=viewer_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == customer_id and body["name"] == "Priya Raman"
    assert body["plan_name"] == "enterprise"
    assert body["subscription"]["customer_id"] == customer_id
    assert body["subscription"]["plan"] == "enterprise"
    assert body["workspace"]["customer_id"] == customer_id and body["workspace"]["name"]
    assert body["tickets"] and {t["customer_id"] for t in body["tickets"]} == {customer_id}
    assert {t["customer_name"] for t in body["tickets"]} == {"Priya Raman"}
    assert [(m["memory_type"], m["content"]) for m in body["memory"]] == [
        ("preference", "Prefers email over chat")
    ]


def test_detail_with_no_memory_has_an_empty_list(client, viewer_headers):
    customer_id = _customer_id(client, viewer_headers, "Marcus Webb")
    assert client.get(f"{CUSTOMERS}/{customer_id}", headers=viewer_headers).json()["memory"] == []


def test_unknown_id_is_404(client, viewer_headers):
    response = client.get(f"{CUSTOMERS}/no-such-customer", headers=viewer_headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_list_shape_and_search(client, viewer_headers):
    page = client.get(CUSTOMERS, headers=viewer_headers).json()
    assert set(page) == {"items", "total", "page", "page_size"}
    assert (page["page"], page["page_size"]) == (1, 20)
    names = [c["name"] for c in page["items"]]
    assert names == sorted(names)

    by_name = client.get(CUSTOMERS, headers=viewer_headers, params={"search": "priya"}).json()
    assert [c["name"] for c in by_name["items"]] == ["Priya Raman"] and by_name["total"] == 1
    none = client.get(CUSTOMERS, headers=viewer_headers, params={"search": "zzzz"}).json()
    assert none["total"] == 0 and none["items"] == []


def test_paging(client, viewer_headers):
    first = client.get(CUSTOMERS, headers=viewer_headers, params={"page_size": 3}).json()
    second = client.get(
        CUSTOMERS, headers=viewer_headers, params={"page_size": 3, "page": 2}
    ).json()
    last = client.get(CUSTOMERS, headers=viewer_headers, params={"page_size": 3, "page": 3}).json()
    assert [len(p["items"]) for p in (first, second, last)] == [3, 3, 2]
    assert first["total"] == 8 and second["page"] == 2
    ids = [c["id"] for p in (first, second, last) for c in p["items"]]
    assert len(set(ids)) == 8


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}])
def test_bad_paging_is_422(client, viewer_headers, params):
    assert client.get(CUSTOMERS, headers=viewer_headers, params=params).status_code == 422
