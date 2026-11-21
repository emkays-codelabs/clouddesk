# Phase 4: system design evolution

> **Status of this phase:** in progress. P4-1 to P4-5 are done (implemented and checked locally). Nothing is deployed.

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

## P4-3: customer API

- `GET /api/v1/customers` (search, page, page_size) and `GET /api/v1/customers/{id}` (`CustomerDetail`, **404** `Customer not found` when unknown) were added in `backend/app/api/customers.py`, open to any authenticated role. `backend/app/services/customer_service.py` assembles the detail from the existing repositories: customer, latest subscription, latest workspace, up to 10 recent tickets as `TicketSummary` and up to 10 memory notes (newest first). No repository method was added.
- The service reuses `_to_summary` from `ticket_service`, so a ticket summary has one shape in both places.
- Checked by `tests/api/test_customers.py`. `main.py` grew by two lines; the Phase 1 line counts were updated.

## P4-4: ticket actions API

- `POST /tickets/{id}/reply`, `/request-info`, `/escalate` (each **201**) and `PATCH /tickets/{id}` (**200**) were added to `backend/app/api/tickets.py`, all role `agent` or `admin` (viewer **403**, unknown ticket **404**). Logic is in `ticket_service.py`; no repository method was added, so the tenant filter stays in the repositories.
- A reply is stored as an `agent` message (author is the caller's email) and honours `internal`. Nothing is sent: the email integration is a mock.
- Transitions are recorded as an internal `system` message ("Status changed from X to Y by <actor>") when `request-info`, `escalate` or `PATCH` actually changes the status. `PATCH` also sets `resolved_at` on `resolved` or `closed` and clears it when the ticket reopens.
- `escalate` writes an `escalations` row with `created_by` `human`, team `Tier 2 Support` (a default, not routing), sets the ticket `escalated` and `escalation_required`.
- Deviation from the contract: the three POST routes return **201** rather than 200. The contract table does not state a code.

## P4-5: dashboard, audit and settings read APIs

- `GET /api/v1/dashboard/summary`, `GET /api/v1/audit` (page, page_size, actor, action; `{items, total}`) and `GET /api/v1/settings` were added in `backend/app/api/{dashboard,audit,settings}.py`, open to any authenticated role. Services: `dashboard_service`, `audit_service`, `settings_service`.
- New tenant-scoped repository aggregates, all in the isolation test: `TicketRepository.count_open`, `count_resolved_since`, `count_by_severity`, `count_by_category`, `resolution_spans`, `ApprovalRepository.count_pending`, `EscalationRepository.count_open`. The average resolution time is computed in Python from the (created, resolved) pairs so it works the same on SQLite and Postgres.
- `by_severity` and `by_category` always list every value, with zeros. `agent_activity` is an empty list until workflow events exist (Phase 10). "Resolved today" counts from UTC midnight.
- `/settings` has response fields only for booleans and names, so no key, URL or password can be serialised. `approval_required_tools` is a constant in `settings_service` until the tool registry exists (Phase 6).
- API tests that count whole-table rows use a private database (`fresh_db` in `tests/api/conftest.py`), because the default test database is shared by the session.
- No contract deviation. `main.py` grew by six lines; the Phase 1 line counts were updated.
