# Phase 10: infrastructure design evolution

> **Status:** implemented. Phase 10 adds no container. It adds a checkpoint store and a background-execution model to the backend.

## A. Overview

The workflow runs inside the backend process. Its state lives in `workflow_runs` (SQLite or Postgres) and its checkpoints in a separate SQLite file.

## B. Initial design

Four containers from earlier phases, with `backend-data` mounted at `/app/data`.

## C. Evolution

`CHECKPOINT_DB_PATH` selects the checkpointer: `:memory:` uses `InMemorySaver` (tests), a file path uses `AsyncSqliteSaver`. The default `./data/checkpoints.db` sits on the existing `backend-data` volume, so paused runs survive a container restart.

## D. Docker

The backend image already contains `agents/`. No new COPY line or package.

## E. Networking

None added. The UI polls the backend over the same REST port.

## F. Wiring

`BackgroundTasks` start a run after the 202 response. Resume goes through `workflow_service.resume_workflow` from the approval route.

## G. Lifecycle commands

`BACKEND_PORT=18000 docker compose up --build -d backend`, then `POST /api/v1/tickets/{id}/run` and `GET /api/v1/tickets/{id}/workflow`.

## H. Environment variables

`CHECKPOINT_DB_PATH` only; it was already in the list.

## I. Persistent storage

`backend-data` holds the application database and the checkpoint file. Deleting the volume loses paused runs.

## J. Health and resilience

Because state is saved after every node, a restart leaves a visible `running` run that must be re-run by a person. This is a known gap.

## K. Observability

`GET /tickets/{id}/events` returns node, tool and model events with duration and tokens; JSON logs carry `workflow_id`.

## L. Final architecture

Unchanged container set; one more file on the data volume.

## M. Verification

Run: the workflow tests offline, and a real run in Docker on the Euron model. Not run: a restart mid-run, Postgres.
