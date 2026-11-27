# Phase 12 explained: the console shell

> **Status:** implemented. Lint, type-check and the Vitest tests pass; a headed Playwright run signed in and used the pages against the Docker stack. Not checked: screen readers, cross-browser behaviour.

## A. Executive summary

Phase 12 builds the signed-in console: an app shell, a typed API client, role-aware login and the list pages. It also carries the public landing page.

## B. Business problem and solution

Support agents need one place to see tickets, customers, knowledge, escalations, approvals and audit, and to sign in with the right role. The console reads the same REST API a script would.

## C. Architecture in simple language

The browser calls the backend only through `frontend/lib/api.ts`. `frontend/lib/auth.tsx` keeps the session. Pages under `frontend/app/(dashboard)/` render data through small components in `frontend/components/`. Navigation is declared once in `frontend/components/layout/nav.ts`.

## D. File-by-file

| File | Purpose |
|---|---|
| `frontend/lib/api.ts` | Typed client: bearer token, 401 redirect, `NetworkError` retry. |
| `frontend/lib/types.ts` | Types mirroring `docs/design/06_API_CONTRACT.md`. |
| `frontend/lib/auth.tsx` | `AuthProvider`, `useAuth`, role helpers. |
| `frontend/lib/hooks.ts` | `usePolling` and fetch hooks. |
| `frontend/lib/format.ts` | Dates, money (INR) and model cost in USD and INR. |
| `frontend/components/layout/AppShell.tsx` | Sidebar, header, Home link, redirect without a session. |
| `frontend/components/ui/` | Button, Card, DataState, StatusPill, KPIStatCards, RiskBadge and others. |
| `frontend/app/login/page.tsx` | Demo-user sign-in. |
| `frontend/app/page.tsx` and `frontend/app/landing.css` | The public landing page. |
| `frontend/app/(dashboard)/` | dashboard, tickets, customers, knowledge, escalations, approvals, agents, audit, settings. |

## E. Execution flow

Open `/`, choose Sign in, pick a demo user, receive a token, land on `/dashboard`. A 401 anywhere returns to `/login?reason=expired`.

## F. Concepts

Role-aware UI: a viewer sees disabled action buttons. `NEXT_PUBLIC_*` values are inlined at build time, so the image is rebuilt per environment.

## G. Decisions

No UI library; a small hand-written kit. The landing page alone uses gradients and its own stylesheet (owner decision, recorded in CLAUDE.md section 11).

## H. Failure handling

`DataState` shows loading, error and empty states. A network failure shows a banner and retries.

## I. Testing

`frontend/__tests__/` covers the API client, auth and formatting helpers, the workflow-step derivation, `StatusPill`, `EmptyState` and nav. `frontend/e2e/console.spec.ts` is a headed Playwright run. Not tested: every page's empty and error states.

## J. Interview-ready explanation

"One typed client, one auth provider, one nav definition, and pages that are thin views over the contract."

## K. Next phase

Phase 13 builds the ticket screen, the only UI that depends on the workflow.
