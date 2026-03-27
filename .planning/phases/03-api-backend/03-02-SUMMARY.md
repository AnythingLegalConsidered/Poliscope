---
phase: 03-api-backend
plan: 02
subsystem: api
tags: [nuxt, drizzle-orm, postgres, h3, pagination, ilike]

# Dependency graph
requires:
  - phase: 03-01
    provides: "getPaginationParams + paginatedResponse helpers, established patterns for filter/pagination/batch tags"
  - phase: 02-data-ingestion
    provides: "618 deputies, 131880 interventions, 12 tags with assignments in DB"
provides:
  - "GET /api/deputies — paginated list, ordered by lastName+firstName ASC, filterable by group and name search"
  - "GET /api/deputies/:id — deputy profile with paginated interventions (with debate context) and tag distribution stats"
affects: [03-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ilike() from drizzle-orm for case-insensitive text search — strip SQL wildcards from input before wrapping with %"
    - "SQL[] conditions array with and(...conditions) — safe to call with 0, 1, or 2 conditions"
    - "count(*) over() window function reused for paginated intervention total inside detail endpoint"
    - "Separate aggregation query for tag distribution (GROUP BY tag) — cleaner than post-processing"

key-files:
  created:
    - server/api/deputies/index.get.ts
    - server/api/deputies/[id].get.ts
  modified: []

key-decisions:
  - "tagStats computed with a separate GROUP BY query (not post-processing in-memory) — covers all deputy interventions, not just the current page"
  - "Interventions in detail endpoint ordered by createdAt DESC (reverse chron, most recent first) rather than orderInDebate ASC"
  - "Debate context included as nested object { title, date } on each intervention — avoids client needing extra requests"

patterns-established:
  - "List endpoint with optional filters: build SQL[] conditions, use and(...conditions) or undefined for WHERE"
  - "Detail endpoint: fetch resource → 404 if missing → paginated related data → batch N-to-M → aggregate stats"

# Metrics
duration: 2min
completed: 2026-03-27
---

# Phase 3 Plan 02: Deputies Endpoints Summary

**Paginated deputy list with political group filter and ilike name search, plus deputy detail endpoint with paginated interventions (debate context via left join), batch tags, and per-deputy tag distribution stats**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-27T22:35:40Z
- **Completed:** 2026-03-27T22:37:26Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- GET /api/deputies returns 618 deputies paginated (default 20/page), ordered by lastName then firstName ASC
- Group filter: `?group=REN` returns 193 deputies exactly matching the group
- Name search: `?search=dupont` uses ilike for case-insensitive partial match, wildcards sanitized
- GET /api/deputies/:id returns full deputy profile with paginated interventions (1806 for deputy 1)
- Each intervention includes debate title and date via left join on debates table
- Batch tag fetch (no N+1) for the current page of interventions
- tagStats: full tag distribution across all deputy interventions (not just current page), sorted by count desc
- Proper error handling: 400 for non-numeric ID, 404 for missing deputy, 500 for DB errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Deputies list endpoint with filters** - `c176d96` (feat)
2. **Task 2: Deputy detail endpoint with interventions and tags** - `478e375` (feat)

## Files Created/Modified
- `server/api/deputies/index.get.ts` — GET /api/deputies, paginated, lastName+firstName ASC, optional group + ilike search
- `server/api/deputies/[id].get.ts` — GET /api/deputies/:id with paginated interventions, debate left join, batch tags, tag distribution stats

## Decisions Made
- tagStats uses a separate `GROUP BY` query covering all interventions for the deputy, not just the current page — gives the full picture of what topics a deputy speaks about
- Interventions ordered by `createdAt DESC` (most recent first) as this is the natural browsing order for a profile page
- Debate context embedded as `{ title, date }` on each intervention to avoid extra API round trips from the client

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both deputy endpoints functional with correct error handling
- Pattern for aggregate stats query (GROUP BY) now established alongside existing batch N-to-M pattern
- 03-03 (full-text search) can build on the ilike pattern and extend to FTS with to_tsquery

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 03-api-backend*
*Completed: 2026-03-27*
