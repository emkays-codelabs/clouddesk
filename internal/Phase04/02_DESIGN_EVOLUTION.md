# Phase 4: system design evolution

> **Status of this phase:** in progress. P4-1 and P4-2 are done (implemented and checked locally); P4-3 to P4-5 are not started. Nothing is deployed.

---

## P4-1: ticket and customer API contract

- Pydantic v2 models for `TicketSummary`, `Ticket`, `TicketMessage`, `TicketDetail`, `Customer`, `CustomerDetail` and the request bodies were added under `backend/app/schemas/`. `TicketDetail` sits in its own module, `ticket_detail.py`, because it needs `Customer` while `CustomerDetail` needs `TicketSummary`; one module would be an import cycle.
- `WorkflowState` is a minimal forward-compatible model (extra keys kept), since the agent phases do not exist yet. `ResolutionAction` and `Escalation` follow the contract.
- `CustomerStatus` and `Plan` were added to `backend/app/schemas/common.py` so the contract's enums have one source.
- The contract was corrected where the models disagreed: severity and category are nullable, `CustomerMemory` carries `confidence`, `Escalation.created_by` is a string, and `channel` defaults to `web`. the frontend type file will mirror it once the frontend exists.
- Checked by `tests/unit/test_ticket_customer_schemas.py`. No routes were added.

## P4-2: ticket API

- `POST /api/v1/tickets` (role `agent` or `admin`, **201**), `GET /api/v1/tickets` (any authenticated role; status, severity, search, page, page_size) and `GET /api/v1/tickets/{id}` (`TicketDetail`, **404** when unknown) were added in `backend/app/api/tickets.py`. The router only does HTTP and role checks; `backend/app/services/ticket_service.py` builds the response models and owns the transaction.
- Creating a ticket writes the ticket and its first `customer` message in one commit and never starts a workflow. Ticket numbers come from `TicketRepository.next_ticket_number()` (numeric maximum of the `CD-` suffix plus one, 1001 for an empty tenant); the service retries up to three times if the unique key refuses a duplicate. That retry is written but not exercised by a test.
- New repository methods, all tenant-scoped and added to the isolation test: `CustomerRepository.get_many`, `EscalationRepository.latest_for_ticket`, `ResolutionActionRepository.list_for_ticket`, `TicketRepository.next_ticket_number`.
- `TicketDetail.workflow` is the latest run's saved state with the run's own columns laid over it; no run exists until `/run` lands, so it is `null` for every ticket today. Seeded tickets have no severity or category, so severity filtering is only exercised after a row is given one.
- The contract gained the 201, the 404s and the paging bounds. `main.py` grew by two lines, so the Phase 1 line count it quotes was updated.
