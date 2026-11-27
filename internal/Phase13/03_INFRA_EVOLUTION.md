# Phase 13: infrastructure design evolution

> **Status:** implemented. No infrastructure change beyond a dev dependency for browser tests.

## A. Overview

The ticket screen ships in the existing frontend container.

## B. Initial design

The Phase 12 image and Compose service.

## C. Evolution

`@playwright/test` was added as a dev dependency with `frontend/playwright.config.ts`. Browsers are installed on the developer's machine, not in the image.

## D. Docker

The production image does not contain Playwright or the frontend e2e folder's browsers.

## E. Networking

The browser reaches the frontend on port 3000 and the backend on the configured host port.

## F. Wiring

`FRONTEND_URL` points the browser test at another address.

## G. Lifecycle commands

`cd frontend && npm run e2e` opens a visible Chromium window and drives the stack.

## H. Environment variables

`FRONTEND_URL` (test only, optional).

## I. Persistent storage

The screenshot `frontend/e2e/last-run.png` is git-ignored.

## J. Health and resilience

The test waits up to six minutes for a real-model run, because each Euron call can take tens of seconds.

## K. Observability

Backend JavaScript Object Notation (JSON) logs show each model call during the browser run.

## L. Final architecture

Unchanged.

## M. Verification

Run: two Playwright tests against the Docker stack. Not run: Continuous integration (CI) browser tests.
