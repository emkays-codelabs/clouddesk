# Phase 11: infrastructure design evolution

> **Status:** implemented. Phase 11 adds no container and no environment variable.

## A. Overview

The approval and escalation code runs in the existing backend container and uses the existing database.

## B. Initial design

The four-container stack with the data volume.

## C. Evolution

Two things in the Makefile and scripts: `make demo` (`scripts/demo.py`) and a refund policy that reads `APPROVAL_REQUIRED_FOR_REFUNDS` and `MAX_REFUND_WITHOUT_APPROVAL` from settings.

## D. Docker

`scripts/` is not copied into the image; the demo runs from the repository, not from the container.

## E. Networking

None added.

## F. Wiring

The approval routes are mounted under `/api/v1/approvals` by `backend/app/main.py`.

## G. Lifecycle commands

`make demo` and `make demo TICKET=CD-1005` run the offline demo. Against the stack: run a refund ticket, list pending approvals, approve.

## H. Environment variables and secrets

`APPROVAL_REQUIRED_FOR_REFUNDS=true`, `MAX_REFUND_WITHOUT_APPROVAL=0` (already listed in CLAUDE.md section 10.1).

## I. Persistent storage

Approvals, actions and escalations live in the application database on `backend-data`.

## J. Health and resilience

A paused run is stored, so a backend restart leaves the approval pending. The approval timeout that would expire it is not built.

## K. Observability

`approval_requested` and `approval_resolved` events appear in `GET /tickets/{id}/events`, and every non-GET request is audited.

## L. Final architecture

Same containers; the database gained live rows in three tables.

## M. Verification

Run: workflow tests and `make demo` offline. Not run: Postgres, multi-approver flows.
