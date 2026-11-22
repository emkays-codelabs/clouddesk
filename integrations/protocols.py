"""Integration protocols: the only surface the tools see of the outside world."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str) -> dict[str, Any]: ...


@runtime_checkable
class BillingService(Protocol):
    async def create_refund(
        self,
        customer_id: str,
        subscription_id: str,
        amount: float,
        reason: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    async def get_refund(self, refund_id: str) -> dict[str, Any] | None: ...


@runtime_checkable
class WorkspaceAdmin(Protocol):
    async def reset_setting(self, workspace_id: str, setting: str) -> dict[str, Any]: ...

    async def get_setting_state(self, workspace_id: str, setting: str) -> str | None: ...


@runtime_checkable
class TicketNotifier(Protocol):
    async def notify(self, ticket_id: str, message: str) -> dict[str, Any]: ...
