# Phase 13 explained: the ticket workflow screen

> **Status:** implemented. A headed Playwright run opened a ticket, started the workflow on the real model and saw it finish; the viewer path was checked as disabled. Not checked: the approve and reject buttons in a browser (covered by application programming interface (API) tests).

## A. Executive summary

One screen, `frontend/app/(dashboard)/tickets/[id]/page.tsx`, lets an agent read the ticket, see the customer, run the artificial intelligence (AI) workflow, watch it progress, inspect evidence and approve, reject, reply, request information or escalate.

## B. Business problem and solution

Agents need to trust what the platform did. The screen shows each step, the evidence with scores, the diagnosis, the planned actions and the draft reply, and keeps human actions one click away.

## C. Architecture in simple language

Three columns: messages and composer on the left, customer panel in the centre, workflow panel on the right. The page polls the workflow route every two seconds until the run ends.

## D. File-by-file

| File | Purpose |
|---|---|
| `frontend/app/(dashboard)/tickets/[id]/page.tsx` | The ticket screen. |
| `frontend/components/tickets/WorkflowSteps.tsx` | Derives the 12 steps and their state from `completed_nodes`. |
| `frontend/components/tickets/EvidencePanel.tsx` | Cited evidence with scores. |
| `frontend/components/tickets/ActionCard.tsx` | A planned action and its approval state. |
| `frontend/components/tickets/ApprovalDiff.tsx` | What approving would change. |
| `frontend/components/tickets/TicketTimeline.tsx` | The event trace. |
| `frontend/app/(dashboard)/customers/[id]/page.tsx` | Customer detail. |
| `frontend/__tests__/WorkflowSteps.test.tsx` | Step derivation. |

## E. Execution flow

Open a ticket, press Run AI workflow, see "Workflow started", watch steps tick, and either see a completed reply or an approval card. Approve or reject; the run resumes or escalates.

## F. Concepts

Polling with `usePolling`; pure derivation of step state from the saved state so the user interface (UI) never guesses.

## G. Decisions

Poll rather than stream (simple, works through any proxy; a two-second lag). Buttons follow the role and the ticket state: approve and reject appear only while an approval is pending.

## H. Failure handling

A failed run shows its errors. A 409 from run, approve or reject is shown as a message, not a crash.

## I. Testing

Vitest covers `WorkflowSteps`; Playwright covers the happy path and the viewer restriction. Not tested in a browser: reject and escalate buttons.

## J. Interview-ready explanation

"The screen is a pure view of the saved workflow state, polled every two seconds, with actions gated by role and ticket status."

## K. Next phase

Phase 14 evaluates and packages the whole system.
