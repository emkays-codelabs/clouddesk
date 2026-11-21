import importlib
import inspect
import pkgutil

import pytest

import app.repositories as repos_pkg
from app.models.entities import DEMO_TENANT_ID, Customer
from app.repositories.base import ScopedRepository
from tests.unit.repositories.conftest import OTHER_TENANT_ID


class _Customers(ScopedRepository[Customer]):
    model = Customer

    async def add(self, obj):
        return await self._add(obj)

    async def get(self, id):
        return await self._get(id)

    async def all(self):
        return (await self.session.execute(self._select())).scalars().all()

    async def update(self, id, **values):
        return await self._update_where(id, **values)

    async def delete(self, *criteria):
        return await self._delete_where(*criteria)

    async def page(self, page, size):
        return await self._page(self._select().order_by(Customer.email), page, size)


def _c(email="a@x.com", **kw):
    return Customer(name="A", email=email, **kw)


async def test_add_stamps_the_repository_tenant(session, tenants):
    c = await _Customers(session).add(_c())
    assert c.tenant_id == DEMO_TENANT_ID
    other = await _Customers(session, OTHER_TENANT_ID).add(_c())
    assert other.tenant_id == OTHER_TENANT_ID


async def test_add_rejects_an_object_carrying_another_tenant(session, tenants):
    with pytest.raises(ValueError):
        await _Customers(session).add(_c(tenant_id=OTHER_TENANT_ID))


async def test_get_returns_none_for_a_row_of_another_tenant(session, tenants):
    c = await _Customers(session, OTHER_TENANT_ID).add(_c())
    assert await _Customers(session).get(c.id) is None
    assert await _Customers(session, OTHER_TENANT_ID).get(c.id) is not None


async def test_select_is_filtered_on_the_tenant(session, tenants):
    await _Customers(session).add(_c("m@x.com"))
    await _Customers(session, OTHER_TENANT_ID).add(_c("o@x.com"))
    rows = await _Customers(session).all()
    assert [r.email for r in rows] == ["m@x.com"]


async def test_update_and_delete_never_touch_another_tenants_row(session, tenants):
    other = await _Customers(session, OTHER_TENANT_ID).add(_c())
    await session.commit()
    other_id = other.id
    repo = _Customers(session)
    assert await repo.update(other_id, name="Hacked") is None
    assert await repo.delete(Customer.id == other_id) == 0
    await session.commit()
    session.expire_all()
    row = await _Customers(session, OTHER_TENANT_ID).get(other_id)
    assert row is not None and row.name == "A"


async def test_page_returns_items_and_total_and_clamps_page_size(session, tenants):
    repo = _Customers(session)
    for i in range(5):
        await repo.add(_c(f"c{i}@x.com"))
    items, total = await repo.page(1, 2)
    assert [i.email for i in items] == ["c0@x.com", "c1@x.com"] and total == 5
    items, _ = await repo.page(3, 2)
    assert [i.email for i in items] == ["c4@x.com"]
    items, _ = await repo.page(1, 0)
    assert len(items) == 1
    items, _ = await repo.page(1, 1000)
    assert len(items) == 5


async def test_created_at_orders_rows_inserted_in_the_same_second(session, tenants):
    repo = _Customers(session)
    ids = [(await repo.add(_c(f"c{i}@x.com"))).id for i in range(5)]
    rows = await repo.all()
    stamps = [r.created_at for r in rows]
    assert len(set(stamps)) == 5
    assert [r.id for r in sorted(rows, key=lambda r: r.created_at)] == ids


def _repo_classes():
    for info in pkgutil.iter_modules(repos_pkg.__path__):
        mod = importlib.import_module(f"app.repositories.{info.name}")
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ == mod.__name__:
                yield cls


def test_no_public_method_takes_a_tenant_id_parameter():
    classes = list(_repo_classes())
    assert classes
    for cls in classes:
        for name, fn in inspect.getmembers(cls, inspect.isfunction):
            # TenantRepository manages the tenants table itself and is the one exception.
            if name.startswith("_") or cls.__name__ == "TenantRepository":
                continue
            assert "tenant_id" not in inspect.signature(fn).parameters, f"{cls.__name__}.{name}"
