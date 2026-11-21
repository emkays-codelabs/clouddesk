# Phase 3: system design evolution

> **Status of this phase:** in progress. P3-1 is written and checked locally only (not yet merged when this was written). P3-2 is written and checked locally only. P3-3 is written and checked locally only. P3-4 has not started, so this document covers only what exists.

---

## P3-1: JWT and `require_role`

**What changed.** The service gained its first security boundary. `backend/app/core/security.py` validates HS256 tokens with PyJWT and exposes `get_current_user` and `require_role(minimum)`, a FastAPI dependency factory over the ranking viewer 1 < agent 2 < admin 3. `Settings.effective_jwt_secret` returns the Supabase secret when set, else `JWT_SECRET`. No new environment variable was added, so `.env.example` is unchanged.

**Decisions.**

| Choice | Reason |
|---|---|
| Algorithm pinned to `["HS256"]` | A token naming `none` or another algorithm is refused, not trusted. |
| `exp` and `sub` required; unknown `role` refused | A token that never expires, or has no known role, is not a credential. |
| One 401 message for every bad token | A caller is not told why a token was refused. |
| 403 for a valid token with too low a role | Separates "who are you" (401) from "you may not" (403). |
| `HTTPBearer(auto_error=False)` | The missing-header 401 carries `WWW-Authenticate: Bearer` from our code. |
| Audience not verified | Supabase tokens carry `aud: authenticated`; the role claim, not the audience, drives access here. |

**Not done.** Nothing in `/api/v1` is protected yet (no such routes exist); the tests use a throwaway app. Token issuing for demo users arrived in P3-2 (below). Behaviour against a real Supabase token is untested.

**Layering.** `backend/app/core/security.py` imports only the settings module, so core stays free of the agent layer. The test fixtures mint tokens through `create_access_token`.

---

## P3-2: Demo auth routes and tokens

**What changed.** `POST /api/v1/auth/demo-login` and `GET /api/v1/auth/me` are mounted from `backend/app/api/auth.py`. Bodies are in `backend/app/schemas/auth.py`; the lookup and token issue live in `backend/app/services/auth_service.py`, so the router holds no rules. The three demo users (`admin@`, `sam.agent@`, `vic.viewer@clouddesk.demo`) did not exist in the database, so `sample_data/profiles.json` was added and the seed service loads it with the rest of the demo data. `ProfileRepository` gained `get_first_by_role`, keeping the tenant filter in the repository.

**Decisions.**

| Choice | Reason |
|---|---|
| 404 when `DEMO_MODE` is false | The route does not appear to exist outside the demo. |
| Login needs `email` or `role`; a mismatch is 401 | Only seeded profiles can log in; nobody is told which part was wrong. |
| Token `sub` is the profile id, TTL 8 hours | `/me` reads the profile by id; matches the P3-1 default. |
| `/me` returns 401 if the profile is gone | A token for a deleted user is not a credential. |
| Responses carry only `access_token`, `token_type`, `user` | No server secret can leak by construction; a test checks the configured secrets never appear. |

**Not done.** No login screen (Phase 12). The routes are not yet behind rate limiting or audit (P3-4 for audit; rate limiting arrived in P3-3, below). Demo tokens signed with the shared demo secret are only as strong as that secret.

---

## P3-3: Redis rate limit

**What changed.** `backend/app/core/redis.py` adds `get_redis()`, a cached async client: real Redis when `REDIS_URL` is set and `USE_FAKE_REDIS` is off, otherwise an in-process fakeredis. `backend/app/middleware/rate_limit.py` is a plain ASGI fixed-window limiter, registered between RequestId and the app, so the order today is CORS, RequestId, RateLimit (Audit joins in P3-4). No new environment variable: `RATE_LIMIT_PER_MINUTE` and `USE_FAKE_REDIS` already existed. `redis` and `fakeredis` are runtime dependencies because the demo runs on fakeredis.

**Decisions.**

| Choice | Reason |
|---|---|
| Key `ratelimit:{client}:{minute}`, `INCR` then `EXPIRE` on the first hit | Fixed window; the counter expires by itself. |
| Client is the socket peer, not `X-Forwarded-For` | A forged header would give a caller a fresh budget. Behind a proxy this needs a trusted-proxy setting (not built). |
| 429 with `Retry-After` and the request id | RequestId and CORS sit outside, so the headers survive. |
| `/health*` exempt | Probes must answer when a client is throttled; tested. |
| Fails open if Redis errors, with a logged error | A limiter outage should not take the API down. |
| Injectable clock; tests clear the `get_redis` cache | No sleeping; no counter leaks between tests. |

**Not done.** No real Redis server was run. The limit is per client address, not per user. Multi-worker behaviour is correct by design (shared Redis) but untested.
