from app.repositories.customers import (
    CustomerRepository,
    SubscriptionRepository,
    WorkspaceRepository,
)
from app.repositories.memory import CustomerMemoryRepository
from app.repositories.tickets import TicketRepository
from app.schemas.common import MemoryType


async def test_the_reads_return_everything_f4_needs_for_one_customer(session, tenants):
    customers = CustomerRepository(session)
    ada = await customers.create(name="Ada", email="ada@x.io")
    bob = await customers.create(name="Bob", email="bob@x.io")
    await SubscriptionRepository(session).create(customer_id=ada.id, plan="pro", seats=8)
    await SubscriptionRepository(session).create(customer_id=bob.id, plan="free", seats=1)
    await WorkspaceRepository(session).create(customer_id=ada.id, name="Ada HQ")
    await WorkspaceRepository(session).create(customer_id=bob.id, name="Bob HQ")

    tickets = TicketRepository(session)
    earlier = [
        await tickets.create(
            ticket_number=f"CD-{i}", customer_id=ada.id, subject=f"old {i}", body="b"
        )
        for i in range(3)
    ]
    current = await tickets.create(
        ticket_number="CD-9", customer_id=ada.id, subject="now", body="b"
    )
    await tickets.create(ticket_number="CD-8", customer_id=bob.id, subject="bob", body="b")

    mem = CustomerMemoryRepository(session)
    for i in range(12):
        await mem.add(customer_id=ada.id, memory_type=MemoryType.note, content=f"ada {i}")
    for i in range(4):
        await mem.add(customer_id=bob.id, memory_type=MemoryType.note, content=f"bob {i}")
    await session.commit()

    assert (await customers.get(ada.id)).email == "ada@x.io"
    assert (await SubscriptionRepository(session).get_for_customer(ada.id)).plan == "pro"
    assert (await WorkspaceRepository(session).get_for_customer(ada.id)).name == "Ada HQ"
    history = await tickets.list_for_customer(ada.id, exclude_ticket_id=current.id)
    assert {t.id for t in history} == {t.id for t in earlier}
    notes = await mem.list_for_customer(ada.id)
    assert len(notes) == 10
    assert all(n.customer_id == ada.id and n.content.startswith("ada") for n in notes)
