"""Tool approval policy (F9, CLAUDE.md 7.4).

An explicit approval bit per tool. A tool that is not in the table always needs approval, so a
newly added or misspelt tool fails closed. Tiers are low/medium/high only (D2 `prohibited` is
not decided and is not built).
"""

from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel

from app.core.config import Settings

RiskTier = Literal["low", "medium", "high"]


class ToolPolicyEntry(BaseModel):
    requires_approval: bool
    risk: RiskTier


DEFAULT_POLICY: dict[str, ToolPolicyEntry] = {
    "get_customer": ToolPolicyEntry(requires_approval=False, risk="low"),
    "get_subscription": ToolPolicyEntry(requires_approval=False, risk="low"),
    "get_ticket_history": ToolPolicyEntry(requires_approval=False, risk="low"),
    "search_docs": ToolPolicyEntry(requires_approval=False, risk="low"),
    "check_service_status": ToolPolicyEntry(requires_approval=False, risk="low"),
    "update_ticket": ToolPolicyEntry(requires_approval=False, risk="medium"),
    "create_escalation": ToolPolicyEntry(requires_approval=False, risk="medium"),
    "reset_demo_setting": ToolPolicyEntry(requires_approval=True, risk="high"),
    "create_refund_request": ToolPolicyEntry(requires_approval=True, risk="high"),
}

# Argument names whose values must come from customer context or an earlier tool result.
DEFAULT_PROVENANCE_FIELDS: dict[str, frozenset[str]] = {
    "create_refund_request": frozenset({"amount", "customer_id", "subscription_id"}),
    "reset_demo_setting": frozenset({"workspace_id"}),
}

REFUND_TOOL = "create_refund_request"


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ToolPolicy:
    def __init__(self, settings: Settings, table: Mapping[str, ToolPolicyEntry] | None = None):
        self._settings = settings
        self._table = dict(DEFAULT_POLICY if table is None else table)

    def requires_approval(self, name: str, args: Mapping[str, Any] | None = None) -> bool:
        entry = self._table.get(name)
        if entry is None:
            return True
        if name == REFUND_TOOL:
            if self._settings.approval_required_for_refunds:
                return True
            amount = _number((args or {}).get("amount"))
            return amount is None or amount > self._settings.max_refund_without_approval
        return entry.requires_approval

    def risk_tier(self, name: str) -> RiskTier:
        entry = self._table.get(name)
        return entry.risk if entry else "high"

    def is_known(self, name: str) -> bool:
        return name in self._table

    def provenance_fields(self, name: str) -> frozenset[str]:
        return DEFAULT_PROVENANCE_FIELDS.get(name, frozenset())


def _normalise(value: Any) -> Any:
    number = _number(value)
    if number is not None:
        return number
    return str(value)


def validate_provenance(
    args: Mapping[str, Any], trusted_values: Iterable[Any], fields: Iterable[str]
) -> list[str]:
    """Return the names of checked arguments whose value is not in the trusted set.

    The trusted set holds ids and amounts taken from customer context or earlier tool results,
    never from ticket text (CLAUDE.md 7.4, 9).
    """
    trusted = {_normalise(v) for v in trusted_values}
    return [f for f in fields if f in args and _normalise(args[f]) not in trusted]
