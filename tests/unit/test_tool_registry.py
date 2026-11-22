"""ToolRegistry.execute (F9, 7.4): approval, timeout, no-raise, idempotency, provenance."""

import asyncio

from app.core.config import Settings
from app.tools.registry import InMemoryIdempotencyStore, ToolRegistry, stable_hash


def make_registry(**overrides) -> tuple[ToolRegistry, list]:
    calls: list = []
    reg = ToolRegistry(Settings(**overrides), store=InMemoryIdempotencyStore())

    async def get_customer(customer_id: str) -> dict:
        """Load a customer."""
        calls.append(("get_customer", customer_id))
        return {"id": customer_id}

    async def create_refund_request(amount: float) -> dict:
        """Request a refund."""
        calls.append(("refund", amount))
        return {"refunded": amount}

    reg.register(get_customer)
    reg.register(create_refund_request, provenance_fields={"amount"})
    return reg, calls


def test_register_uses_docstring_as_description():
    reg, _ = make_registry()
    assert reg.describe("get_customer") == "Load a customer."
    assert {t["name"] for t in reg.list_tools()} == {"get_customer", "create_refund_request"}


async def test_read_tool_runs_without_approval():
    reg, calls = make_registry()
    res = await reg.execute("get_customer", {"customer_id": "c1"})
    assert res.ok and res.data == {"id": "c1"} and calls == [("get_customer", "c1")]


async def test_unknown_tool_requires_approval_and_does_not_run():
    reg, _ = make_registry()
    res = await reg.execute("drop_database", {})
    assert not res.ok and res.error == "approval_required"
    res = await reg.execute("drop_database", {}, approved=True)
    assert not res.ok and res.error == "unknown_tool"


async def test_approval_required_tool_is_not_run_without_approval():
    reg, calls = make_registry()
    res = await reg.execute("create_refund_request", {"amount": 10}, trusted_values={10})
    assert not res.ok and res.error == "approval_required" and calls == []


async def test_approved_refund_runs():
    reg, calls = make_registry()
    res = await reg.execute(
        "create_refund_request", {"amount": 10}, approved=True, trusted_values={10}
    )
    assert res.ok and calls == [("refund", 10)]


async def test_raising_tool_returns_not_ok():
    reg = ToolRegistry(Settings())

    async def get_customer() -> None:
        """Boom."""
        raise RuntimeError("db down")

    reg.register(get_customer)
    res = await reg.execute("get_customer", {})
    assert not res.ok and "db down" in res.error


async def test_bad_arguments_return_not_ok():
    reg, _ = make_registry()
    res = await reg.execute("get_customer", {"nope": 1})
    assert not res.ok


async def test_slow_tool_times_out():
    reg = ToolRegistry(Settings(tool_timeout_seconds=0.05))

    async def get_customer() -> None:
        """Slow."""
        await asyncio.sleep(2)

    reg.register(get_customer)
    res = await reg.execute("get_customer", {})
    assert not res.ok and res.error == "timeout"


async def test_same_call_twice_runs_tool_once():
    reg, calls = make_registry()
    first = await reg.execute("get_customer", {"customer_id": "c1"}, ticket_id="T1")
    second = await reg.execute("get_customer", {"customer_id": "c1"}, ticket_id="T1")
    assert len(calls) == 1
    assert second.ok and second.data == first.data
    assert second.idempotent is True and first.idempotent is False


async def test_different_ticket_or_args_run_again():
    reg, calls = make_registry()
    await reg.execute("get_customer", {"customer_id": "c1"}, ticket_id="T1")
    await reg.execute("get_customer", {"customer_id": "c1"}, ticket_id="T2")
    await reg.execute("get_customer", {"customer_id": "c2"}, ticket_id="T1")
    assert len(calls) == 3


async def test_failed_call_is_not_cached():
    reg = ToolRegistry(Settings())
    state = {"n": 0}

    async def get_customer() -> dict:
        """Flaky."""
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("once")
        return {"ok": True}

    reg.register(get_customer)
    assert not (await reg.execute("get_customer", {}, ticket_id="T")).ok
    assert (await reg.execute("get_customer", {}, ticket_id="T")).ok


async def test_refund_amount_from_ticket_text_rejected_but_subscription_amount_accepted():
    reg, calls = make_registry()
    bad = await reg.execute(
        "create_refund_request", {"amount": 999}, approved=True, trusted_values={120.0}
    )
    assert not bad.ok and bad.error == "provenance_failed" and calls == []
    good = await reg.execute(
        "create_refund_request", {"amount": 120}, approved=True, trusted_values={120.0}
    )
    assert good.ok and calls == [("refund", 120)]


async def test_missing_trusted_values_fails_provenance_closed():
    reg, calls = make_registry()
    res = await reg.execute("create_refund_request", {"amount": 5}, approved=True)
    assert not res.ok and res.error == "provenance_failed" and calls == []


def test_stable_hash_ignores_key_order():
    assert stable_hash({"a": 1, "b": [2, 3]}) == stable_hash({"b": [2, 3], "a": 1})
    assert stable_hash({"a": 1}) != stable_hash({"a": 2})


async def test_execute_never_raises_on_unserialisable_args():
    reg, _ = make_registry()
    res = await reg.execute("get_customer", {"customer_id": object()})
    assert isinstance(res.ok, bool)


async def test_non_idempotent_tool_runs_every_time():
    reg, calls = make_registry()

    async def search_docs() -> str:
        """Ping."""
        calls.append("ping")
        return "pong"

    reg.register(search_docs, idempotent=False)
    first = await reg.execute("search_docs", {})
    second = await reg.execute("search_docs", {})
    assert first.ok and second.ok and not second.idempotent
    assert calls.count("ping") == 2
