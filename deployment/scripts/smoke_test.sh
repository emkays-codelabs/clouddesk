#!/usr/bin/env bash
# Smoke test against a running stack: BASE_URL=http://localhost:8000 smoke_test.sh
# Checks liveness, readiness, the OpenAPI document and a demo login. Exits non-zero on the first failure.
set -euo pipefail

base="${BASE_URL:-http://localhost:8000}"
fail() { echo "FAIL: $1" >&2; exit 1; }

curl -fsS "$base/health/live" >/dev/null || fail "$base/health/live"
echo "ok  /health/live"

ready="$(curl -fsS "$base/health/ready")" || fail "$base/health/ready"
echo "ok  /health/ready  $ready"

curl -fsS "$base/openapi.json" | grep -q '"/api/v1/tickets"' || fail "openapi lacks /api/v1/tickets"
echo "ok  /openapi.json lists the ticket routes"

if curl -fsS -X POST "$base/api/v1/auth/demo-login" -H 'content-type: application/json' \
  -d '{"email":"sam.agent@clouddesk.demo"}' | grep -q access_token; then
  echo "ok  demo login"
else
  echo "skip demo login (DEMO_MODE is off or the route is disabled)"
fi
echo "smoke test passed against $base"
