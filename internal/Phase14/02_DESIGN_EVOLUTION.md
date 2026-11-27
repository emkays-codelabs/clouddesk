# Phase 14: system design evolution

> **Status:** complete and validated locally. P14-1 to P14-5 are done. The stack was brought up in Docker; the Terraform roots were validated only; no workflow has run on GitHub; nothing is deployed.

---

## P14-1: Evaluation thresholds

`tests/evaluation/test_eval_thresholds.py` runs the 13 ticket cases through `POST /tickets/{id}/run` on the fake model and the 3 text-only cases through the rules and retriever, then checks classification, retrieval hit-rate@3, escalation correctness, citation rate and grounding rate against the CLAUDE.md section 13 floors. Each test uses a private database (`tests/evaluation/conftest.py`) because the shared one remembers earlier runs. These measure the offline pipeline, not a real model.

## P14-2: Backend and frontend Dockerfiles

`backend/Dockerfile` is multi-stage `python:3.12-slim`, built from the repo root, non-root `app`, HEALTHCHECK on `/health/live`. `frontend/Dockerfile` is `node:22-alpine` standalone, non-root, HEALTHCHECK on `/api/health`. Built ahead of the graph at the owner's request and brought up healthy on 2026-11-27.

## P14-3: Compose stack

`docker-compose.yml`: frontend, backend, redis (`redis:7-alpine`) and qdrant, all `service_healthy`, named volumes, `restart: unless-stopped`, real Redis. Host ports come from `BACKEND_PORT` and `FRONTEND_PORT`; the stack ran on 18000 because 8000 was in use.

## P14-4: Terraform and CI scaffolds

One root per cloud under `deployment/` (`deployment/aws/main.tf`, `deployment/azure/main.tf`, `deployment/gcp/main.tf`) with registry, secrets, compute, load balancing, monitoring, Redis and networking declared per cloud. Var-files `deployment/environments/{dev,staging,prod}.tfvars`. Five scripts under `deployment/scripts/` and five workflows under `.github/workflows/`. `make terraform-validate` passes for all three. The CLAUDE.md section 20 contradiction about terraform.tfvars is resolved by naming the files `<env>.tfvars`.

## P14-5: Deployment hygiene tests

`tests/deployment/test_delivery.py` checks the roots, sensitive variables, var-files, script strictness and syntax, the `--auto-approve` rule, SHA tagging, workflow structure and ordering, no embedded credential, the Makefile targets and no committed `.env`. `make smoke` passed against the local stack.

---

## Limitations

No `terraform plan` or `apply`, no application database in the scaffolds, no checkov or Trivy run, no CI run, and no harder evaluation bar or red-team set (D6).
