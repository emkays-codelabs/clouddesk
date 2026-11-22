"""In-memory mock adapters. Each records its calls so a test or the demo can inspect them.

No network, no email, no refund ever leaves the process.
"""

import itertools
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RecordedCall:
    method: str
    args: dict[str, Any]


@dataclass
class _Recorder:
    calls: list[RecordedCall] = field(default_factory=list)

    def record(self, method: str, **args: Any) -> None:
        self.calls.append(RecordedCall(method, args))


class MockEmailSender(_Recorder):
    async def send(self, to: str, subject: str, body: str) -> dict[str, Any]:
        self.record("send", to=to, subject=subject, body=body)
        return {"status": "recorded", "to": to, "subject": subject}


class MockTicketNotifier(_Recorder):
    async def notify(self, ticket_id: str, message: str) -> dict[str, Any]:
        self.record("notify", ticket_id=ticket_id, message=message)
        return {"status": "recorded", "ticket_id": ticket_id}


class MockBillingService(_Recorder):
    def __init__(self) -> None:
        super().__init__()
        self.refunds: dict[str, dict[str, Any]] = {}
        self._by_key: dict[str, str] = {}
        self._ids = itertools.count(1)

    async def create_refund(
        self,
        customer_id: str,
        subscription_id: str,
        amount: float,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        self.record(
            "create_refund",
            customer_id=customer_id,
            subscription_id=subscription_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key,
        )
        existing = self._by_key.get(idempotency_key)
        if existing is not None:
            return self.refunds[existing]
        refund_id = f"re_mock_{next(self._ids):04d}"
        refund = {
            "id": refund_id,
            "status": "recorded",
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "amount": amount,
            "reason": reason,
        }
        self.refunds[refund_id] = refund
        self._by_key[idempotency_key] = refund_id
        return refund

    async def get_refund(self, refund_id: str) -> dict[str, Any] | None:
        return self.refunds.get(refund_id)


class MockWorkspaceAdmin(_Recorder):
    def __init__(self) -> None:
        super().__init__()
        self._state: dict[tuple[str, str], str] = {}

    async def reset_setting(self, workspace_id: str, setting: str) -> dict[str, Any]:
        self.record("reset_setting", workspace_id=workspace_id, setting=setting)
        self._state[(workspace_id, setting)] = "reset"
        return {"status": "recorded", "workspace_id": workspace_id, "setting": setting}

    async def get_setting_state(self, workspace_id: str, setting: str) -> str | None:
        return self._state.get((workspace_id, setting))
