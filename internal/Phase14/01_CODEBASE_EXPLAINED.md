# Phase 14 explained: evaluation and delivery

> **Status:** implemented and validated locally. No cloud credentials were used, nothing was applied to a real account, and no GitHub Actions workflow has run.

## A. Executive summary

Phase 14 proves the system meets quality floors and packages it for delivery: evaluation thresholds that fail the build, Dockerfiles and Compose, Terraform scaffolds for three clouds, deploy scripts, workflows and a smoke test.

## B. Business problem and solution

A demo that "seems fine" is not evidence. The thresholds put numbers on classification, retrieval, escalation, citation and grounding; the delivery files make the same artifact reproducible anywhere.

## C. Architecture in simple language

`tests/evaluation/test_eval_thresholds.py` runs every ticket case in `datasets/eval_cases.json` through the real workflow application programming interface (API) on the fake model and checks five metrics. `deployment/` holds one Terraform root per cloud and shared per-environment var-files. `.github/workflows/` holds the five pipelines.

## D. File-by-file

| File | Purpose |
|---|---|
| `tests/evaluation/test_eval_thresholds.py` | The five thresholds. |
| `tests/evaluation/conftest.py` | A private database per test. |
| `datasets/eval_cases.json` | 16 cases: 13 demo tickets, 3 text-only. |
| `backend/Dockerfile`, `frontend/Dockerfile` | Images, non-root, health-checked. |
| `docker-compose.yml` | The five-service stack: frontend, backend, postgres, redis, qdrant. |
| `deployment/aws/main.tf`, `deployment/azure/main.tf`, `deployment/gcp/main.tf` | Per-cloud infrastructure. |
| `deployment/environments/dev.tfvars` | Dev settings; staging and prod sit beside it. |
| `deployment/scripts/deploy.sh` | Plan and apply; refuses `--auto-approve` outside dev. |
| `deployment/scripts/smoke_test.sh` | Checks liveness, readiness, OpenAPI and demo login. |
| `.github/workflows/_deploy.yml` | The reusable deploy pipeline. |
| `tests/deployment/test_delivery.py` | Static checks of all of the above. |
| `frontend/e2e/console.spec.ts` | Headed browser test. |

## E. Execution flow

`make test` runs the thresholds with everything else. `make terraform-validate` initialises each root without a backend and validates it. `BASE_URL=http://localhost:18000 make smoke` checks a running stack.

## F. Concepts

Thresholds fail the build and are never lowered to pass. Image tags are git Secure Hash Algorithms (SHAs). Secrets reach Terraform only through `TF_VAR_*`. Var-files are named `dev.tfvars` and so on, not terraform.tfvars, which resolves the contradiction between committing var-files and ignoring that name.

## G. Decisions and trade-offs

Each cloud root is flat files per concern, not shared modules: Terraform modules cannot be shared across providers, so the "shared" part is the var-files and scripts. The v1 gate is the lower bar in CLAUDE.md section 13; the harder bar and a red-team set (D6) are not built.

## H. Failure handling

`build_and_push.sh` refuses a dirty tree. `deploy.sh` and `destroy.sh` ask for typed confirmation. The deploy pipeline gates prod through the GitHub Environment `prod-apply`.

## I. Testing

Run: the evaluation suite, `make terraform-validate` for all three clouds, the delivery tests, the smoke test against the local stack, the Docker bring-up. Not run: `terraform plan` or `apply`, any GitHub workflow, any cloud, real-model evaluation.

## J. Interview-ready explanation

"We measure five metrics offline and fail the build below the floor, and everything we ship is validated but unapplied, which we state plainly."

## K. Takeaways

The system is complete for the v1 scope. The remaining work is in CLAUDE.md section 20.
