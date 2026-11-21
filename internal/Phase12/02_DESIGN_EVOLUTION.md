# Phase 12: system design evolution

> **Status of this phase:** in progress. P12-1 (app shell and navigation) is built and checked locally; P12-2 to P12-4 are not started. Nothing is deployed and the frontend does not call the backend yet.

---

## P12-1: Next.js app shell and navigation

- **What exists.** `frontend/` is a Next.js 15 App Router app (TypeScript, Tailwind 3, ESLint, Vitest with jsdom). Versions are pinned exactly in `package.json`, with `package-lock.json` committed. `next.config.mjs` sets `output: "standalone"` so a later Dockerfile can copy the standalone server.
- **Layout.** The `(dashboard)` route group wraps the eight console pages (`/dashboard`, `/tickets`, `/customers`, `/knowledge`, `/escalations`, `/agents`, `/audit`, `/settings`) in a sidebar. `/login` sits outside the group. `/` redirects to `/dashboard`. Every page is a placeholder.
- **Navigation is declared once** in `frontend/components/layout/nav.ts`; the sidebar only renders that list, and a test pins the list to the eight pages.
- **UI kit.** `frontend/components/ui/` holds Button, Card, StatusPill, EmptyState, Spinner and PagePlaceholder. No UI library and no gradients.
- **Health.** `GET /api/health` returns `{"status":"ok"}` for the future container HEALTHCHECK.
- **Tooling.** `.claude/hooks/pre-commit.sh` also runs the frontend lint and tests when `frontend/node_modules` exists.
- **Planned, not built.** The API client, auth and role-aware layout (P12-2, P12-3), and the data pages (P12-4). `NEXT_PUBLIC_API_URL` is not read yet.
