---
phase: 13-api-rest-universelle-openapi
plan: 01
subsystem: api
tags: [nuxt, h3, drizzle-orm, postgresql, votes, scrutins, bicameral]

# Dependency graph
requires:
  - phase: 12-ingestion-votes-scrutins
    provides: 7062 scrutins + 1308512 votes ingested in DB (scrutins + votes tables)
  - phase: 11-ingestion-debats-senat
    provides: actors.chamber column, bicameral actor dataset (577 AN + 348 senators)
provides:
  - GET /api/votes — paginated scrutins list with chambre/dateFrom/dateTo/result filters
  - GET /api/votes/:id — scrutin detail + paginated per-actor votes with position filter
  - GET /api/deputies?chamber=AN|Senat — chamber filter on actors list
  - GET /api/deputies/:id response includes voteStats (position counts per actor)
affects: [14-frontend-votes, 15-openapi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Drizzle window function count(*) over() for paginated totals without COUNT query
    - conditions array + and(...conditions) for composable WHERE clauses
    - getPaginationParams + paginatedResponse auto-imported from server/utils

key-files:
  created:
    - packages/web/server/api/votes/index.get.ts
    - packages/web/server/api/votes/[id].get.ts
  modified:
    - packages/web/server/api/deputies/index.get.ts
    - packages/web/server/api/deputies/[id].get.ts

key-decisions:
  - "chambre query param on /api/votes (not chamber) — matches AN data variable naming convention"
  - "votes/[id].get.ts paginates per-actor votes (mandatory — 1.3M votes total, cannot return all)"
  - "voteStats added to deputy profile — enables Phase 14 frontend to show vote breakdown"
  - "debates/[id].get.ts skipped — full select() already returns chamber in response"

patterns-established:
  - "Votes API: exact same pattern as debates (getPaginationParams, conditions array, window function count, paginatedResponse)"
  - "Position filter validated against whitelist ['for', 'against', 'abstain', 'absent'] before eq()"

# Metrics
duration: 15min
completed: 2026-04-01
---

# Phase 13 Plan 01: Votes API Endpoints Summary

**REST endpoints for 7062 scrutins and 1.3M votes: GET /api/votes (list + filters) and GET /api/votes/:id (detail + paginated per-actor votes), plus chamber filter on deputies**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-01T05:45:56Z
- **Completed:** 2026-04-01T06:01:15Z
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- Created `GET /api/votes` — paginated scrutins list with 4 composable query filters (chambre, dateFrom, dateTo, result)
- Created `GET /api/votes/:id` — scrutin detail with paginated per-actor votes, LEFT JOIN actors for name/group/photo, optional position filter
- Added `?chamber=AN|Senat` filter to `GET /api/deputies`
- Added `voteStats` (position breakdown counts) to `GET /api/deputies/:id` response

## Task Commits

Each task was committed atomically:

1. **Task 1: Create GET /api/votes endpoints (list + detail)** - `33b66e6` (feat)
2. **Task 2: Add chamber filter to deputies and voteStats to deputy profile** - `e900153` (feat)

**Plan metadata:** (committed with SUMMARY below)

## Files Created/Modified
- `packages/web/server/api/votes/index.get.ts` — Paginated scrutins list, chambre/date/result filters, desc(date) order
- `packages/web/server/api/votes/[id].get.ts` — Scrutin metadata + paginated votes with leftJoin(actors), optional position filter
- `packages/web/server/api/deputies/index.get.ts` — Added ?chamber=AN|Senat condition to WHERE builder
- `packages/web/server/api/deputies/[id].get.ts` — Added votes import + voteStats query (GROUP BY position), added to return object

## Decisions Made
- `chambre` (not `chamber`) param on `/api/votes` — consistent with AN field naming (the plan specified this spelling)
- Pagination mandatory on votes/[id]: 1.3M votes in DB, cannot return all in single response
- `votes/[id].get.ts` orders by `asc(actors.lastName)` for alphabetical vote display
- `debates/[id].get.ts` required no changes — `select()` without field list already returns all columns including `chamber`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- `npx nuxi typecheck` fails with a pre-existing environment issue (vue-tsc not locally installed, pulled via npx with mismatched `@vue/language-core` version). Errors are on `nuxt.config.ts` (process.env types), not on the new files. Code review confirms correct imports and usage patterns — `gte`/`lte` confirmed exported from `drizzle-orm` via `sql/expressions/conditions`.
- Dev server not running in shell environment (requires DATABASE_URL with LXC credentials). Functional curl tests deferred to manual verification on next dev session.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `/api/votes` and `/api/votes/:id` are ready for Phase 14 frontend consumption
- `/api/deputies?chamber=AN|Senat` ready for bicameral actor filtering in UI
- Deputy profiles now expose `voteStats` for vote breakdown display
- Phase 13 Plan 02 can proceed: OpenAPI schema + Scalar UI, FTS cross-type search

---
*Phase: 13-api-rest-universelle-openapi*
*Completed: 2026-04-01*
