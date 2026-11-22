"""Pick the integration adapters. v1 has mocks only, so anything but demo mode is refused."""

from dataclasses import dataclass

from integrations.mock.services import (
    MockBillingService,
    MockEmailSender,
    MockTicketNotifier,
    MockWorkspaceAdmin,
)
from integrations.protocols import BillingService, EmailSender, TicketNotifier, WorkspaceAdmin


class IntegrationsNotAvailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Integrations:
    email: EmailSender
    billing: BillingService
    workspace_admin: WorkspaceAdmin
    notifier: TicketNotifier


_bundle: Integrations | None = None


def get_integrations(demo_mode: bool) -> Integrations:
    """The process-wide bundle of mocks (shared so their recorded calls can be inspected)."""
    global _bundle
    if not demo_mode:
        raise IntegrationsNotAvailable("no real adapters exist in v1; run with DEMO_MODE=true")
    if _bundle is None:
        _bundle = Integrations(
            email=MockEmailSender(),
            billing=MockBillingService(),
            workspace_admin=MockWorkspaceAdmin(),
            notifier=MockTicketNotifier(),
        )
    return _bundle


def reset_integrations() -> None:
    global _bundle
    _bundle = None
