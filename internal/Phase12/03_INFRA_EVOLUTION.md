# Phase 12: infrastructure design evolution

> **Status:** implemented. The frontend image was rebuilt and served the console in Docker.

## A. Overview

The frontend is a Next.js standalone server in its own container.

## B. Initial design

`frontend/Dockerfile` on `node:22-alpine`, non-root, HEALTHCHECK on `/api/health`.

## C. Evolution

`lucide-react` (exact pin) and `@playwright/test` (dev) joined `frontend/package.json`. The landing and console styles are bundled by Next.js.

## D. Docker

Three stages (deps, builder, runner). `NEXT_PUBLIC_API_URL` is a build argument.

## E. Networking

The browser, not the container, calls the backend, so the uniform resource locator (URL) is the host port (`http://localhost:${BACKEND_PORT:-8000}`). Here the backend ran on 18000 because 8000 was in use.

## F. Wiring

`frontend` depends on `backend` being healthy.

## G. Lifecycle commands

`BACKEND_PORT=18000 docker compose up --build -d frontend`; then open `http://localhost:3000`. `cd frontend && npm run e2e` runs the headed browser test.

## H. Environment variables

`NEXT_PUBLIC_API_URL` and the optional `NEXT_PUBLIC_USD_INR` display rate (default 85, an estimate used only for showing cost in Indian rupees (INR)).

## I. Persistent storage

None in the frontend.

## J. Health and resilience

`/api/health` is the probe. The client retries after a network error.

## K. Observability

Browser errors are not collected; the backend logs carry request ids returned in `X-Request-ID`.

## L. Final architecture

Unchanged container set.

## M. Verification

Run: Docker build, lint, type-check, Vitest, headed Playwright against the stack. Not run: Lighthouse, mobile devices.
