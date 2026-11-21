# Phase 4: system design evolution

> **Status of this phase:** in progress. Only P4-1 is done (implemented and checked locally); P4-2 to P4-5 are not started. Nothing is deployed.

---

## P4-1: ticket and customer API contract

- Pydantic v2 models for `TicketSummary`, `Ticket`, `TicketMessage`, `TicketDetail`, `Customer`, `CustomerDetail` and the request bodies were added under `backend/app/schemas/`. `TicketDetail` sits in its own module, `ticket_detail.py`, because it needs `Customer` while `CustomerDetail` needs `TicketSummary`; one module would be an import cycle.
- `WorkflowState` is a minimal forward-compatible model (extra keys kept), since the agent phases do not exist yet. `ResolutionAction` and `Escalation` follow the contract.
- `CustomerStatus` and `Plan` were added to `backend/app/schemas/common.py` so the contract's enums have one source.
- The contract was corrected where the models disagreed: severity and category are nullable, `CustomerMemory` carries `confidence`, `Escalation.created_by` is a string, and `channel` defaults to `web`. the frontend type file will mirror it once the frontend exists.
- Checked by `tests/unit/test_ticket_customer_schemas.py`. No routes were added.
