---
phase: 03-api-backend
plan: 01
subsystem: api
tags: [nuxt, drizzle-orm, postgres, pagination, h3]

# Dependency graph
requires:
  - phase: 02-data-ingestion
    provides: "Populated DB with 618 deputies, 257 debates, 131880 interventions, 12 tags"
  - phase: 01-scaffold
    provides: "Nuxt 4 app with Drizzle schema, db utility, health endpoint"
provides:
  - "GET /api/debates — paginated list, ordered by date desc"
  - "GET /api/debates/:id — debate detail with interventions, deputy info, and tags"
  - "server/utils/pagination.ts — shared getPaginationParams + paginatedResponse helpers"
affects: [03-02, 03-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "count(*) over() window function for paginated total count in single query"
    - "Batch tag fetch with inArray() to avoid N+1 on detail endpoints"
    - "Relative schema imports (../../db/schema) instead of ~ alias in server/api files"
    - "Re-throw H3 createError instances as-is, wrap unexpected errors in 500"

key-files:
  created:
    - server/utils/pagination.ts
    - server/api/debates/index.get.ts
    - server/api/debates/[id].get.ts
    - .env
  modified:
    - package-lock.json

key-decisions:
  - "Use relative imports (../../db/schema) not ~ alias — Nuxt 4 resolves ~ to app/ not root"
  - "getPaginationParams accepts H3Event directly (not raw query object) for cleaner API"
  - "Interventions include deputy object (null if no match) and tags array — always present on detail"

patterns-established:
  - "Pagination: getPaginationParams(event) + paginatedResponse(data, total, page, limit)"
  - "Detail endpoint: fetch resource, 404 if missing, join related data, batch fetch N-to-M"
  - "Error handling: re-throw H3 errors, wrap DB errors in 500"

# Metrics
duration: 25min
completed: 2026-03-27
---

# Phase 3 Plan 01: Foundation + Debates Endpoints Summary

**Shared pagination utility + GET /api/debates (paginated list) + GET /api/debates/:id (full detail with interventions, deputy joins, and batch-fetched tags) using Drizzle ORM on Nuxt 4**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-27T22:10:00Z
- **Completed:** 2026-03-27T22:35:00Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments
- Pagination utility reusable by all future list endpoints
- GET /api/debates returns 257 debates paginated (default 20/page, max 100), ordered by date desc
- GET /api/debates/:id returns full debate + all interventions with deputy info (left join) and tags (batch query, no N+1)
- Proper error handling: 400 for non-numeric ID, 404 for missing debate, 500 for DB errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Pagination utility + debates list endpoint** - `5446b8d` (feat)
2. **Task 2: Debate detail endpoint with interventions** - `c79932f` (feat)
3. **Chore: package-lock.json** - `0e82642` (chore)

## Files Created/Modified
- `server/utils/pagination.ts` — getPaginationParams(event) + paginatedResponse<T>() helpers
- `server/api/debates/index.get.ts` — GET /api/debates, paginated, date desc, single-query total count
- `server/api/debates/[id].get.ts` — GET /api/debates/:id with leftJoin deputies, batch tags
- `.env` — Created from .env.example (not committed, in .gitignore)
- `package-lock.json` — Generated from first npm install on this machine

## Decisions Made
- `getPaginationParams` takes `H3Event` not raw query — cleaner, avoids re-calling `getQuery` in handler
- Used relative imports `../../db/schema` instead of `~/server/db/schema` — Nuxt 4 resolves `~` to `app/` directory, breaking server imports
- Tags always returned as array (empty `[]` if none) — consistent API shape

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing .env file + npm dependencies**
- **Found during:** Pre-task setup
- **Issue:** No `.env` file existed, node_modules not installed — server couldn't start
- **Fix:** Created `.env` from `.env.example`, ran `npm install`, ran ingestion pipeline to populate fresh DB
- **Files modified:** `.env` (not committed), `package-lock.json`
- **Verification:** Server started, health endpoint working, DB populated with 257 debates and 131880 interventions
- **Committed in:** `0e82642` (package-lock.json only; .env in .gitignore)

**2. [Rule 1 - Bug] Wrong import path using ~ alias**
- **Found during:** Task 1 (debates list endpoint)
- **Issue:** `import { debates } from '~/server/db/schema'` failed — Nuxt 4 resolves `~` to `app/` not project root
- **Fix:** Changed to relative import `../../db/schema` in all server/api files
- **Files modified:** `server/api/debates/index.get.ts`
- **Verification:** Server reloaded, endpoint returned data correctly
- **Committed in:** `5446b8d` (fixed before Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for the server to run at all. No scope creep.

## Issues Encountered
- Docker Desktop was not running at session start — started it manually
- Fresh Docker volume meant DB was empty — ran full ingestion pipeline (257 debates, 131880 interventions, 8min)

## User Setup Required
None - no external service configuration required beyond the existing .env.example pattern.

## Self-Check: PASSED

All files verified present. All commits verified in git log.

## Next Phase Readiness
- Pagination helper ready for 03-02 (deputies endpoints) and 03-03 (search)
- Pattern established: relative schema imports, batch N-to-M fetch, H3 error re-throw
- DB fully populated with production-like dataset (257 debates, 131880 interventions)

---
*Phase: 03-api-backend*
*Completed: 2026-03-27*
