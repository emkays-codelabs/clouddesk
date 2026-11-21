from app.repositories.customers import (
    CustomerRepository,
    SubscriptionRepository,
    WorkspaceRepository,
)


async def _seed(session):
    repo = CustomerRepository(session)
    a = await repo.create(name="Ada Lovelace", email="ada@acme.io", company="Analytical")
    b = await repo.create(name="Bob", email="bob@beta.io", company="Beta_Co")
    c = await repo.create(name="Cy", email="cy@gamma.io", company="100% Gamma")
    await session.commit()
    return repo, a, b, c


async def test_create_get_and_get_by_email_round_trip(session, tenants):
    repo, a, _, _ = await _seed(session)
    assert (await repo.get(a.id)).email == "ada@acme.io"
    assert (await repo.get_by_email("ada@acme.io")).id == a.id
    assert await repo.get_by_email("nobody@x.io") is None


async def test_search_matches_name_email_and_company_case_insensitively(session, tenants):
    repo, a, b, _ = await _seed(session)
    for term, expected in [("LOVELACE", a), ("BETA.IO", b), ("analytical", a)]:
        items, total = await repo.list(search=term)
        assert [i.id for i in items] == [expected.id] and total == 1


async def test_search_treats_percent_and_underscore_literally(session, tenants):
    repo, _, b, c = await _seed(session)
    assert [i.id for i in (await repo.list(search="100%"))[0]] == [c.id]
    # "_" would match every row if it were a LIKE wildcard; only Beta_Co contains it.
    assert [i.id for i in (await repo.list(search="_"))[0]] == [b.id]


async def test_list_returns_total_across_pages(session, tenants):
    repo, *_ = await _seed(session)
    items, total = await repo.list(page=1, page_size=2)
    assert len(items) == 2 and total == 3
    items, total = await repo.list(page=2, page_size=2)
    assert len(items) == 1 and total == 3


async def test_subscription_and_workspace_for_customer(session, tenants):
    repo, a, b, _ = await _seed(session)
    subs, spaces = SubscriptionRepository(session), WorkspaceRepository(session)
    await subs.create(customer_id=a.id, plan="pro", seats=8)
    await subs.create(customer_id=b.id, plan="free", seats=1)
    await spaces.create(customer_id=a.id, name="Acme HQ", member_count=5)
    await session.commit()
    assert (await subs.get_for_customer(a.id)).seats == 8
    assert (await spaces.get_for_customer(a.id)).name == "Acme HQ"
    assert await spaces.get_for_customer(b.id) is None


async def test_get_many_returns_only_the_requested_ids(session, tenants):
    repo, a, b, _ = await _seed(session)
    found = await repo.get_many([a.id, b.id, "missing"])
    assert set(found) == {a.id, b.id} and found[a.id].name == "Ada Lovelace"
    assert await repo.get_many([]) == {}
