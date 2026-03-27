---
phase: 03-api-backend
plan: "03"
subsystem: api
tags: [nuxt, postgres, drizzle, full-text-search, fts, french, ts_rank, ts_headline, websearch_to_tsquery]

requires:
  - phase: 03-01
    provides: pagination utility (getPaginationParams, paginatedResponse) and debates endpoints
  - phase: 03-02
    provides: deputies endpoints and schema with intervention_tags/tags tables
  - phase: 01-02
    provides: Drizzle schema with GIN FTS index on interventions.content

provides:
  - GET /api/search — full-text search over French intervention text with ranking and highlights
  - Filter support: deputyId, debateId, tag slug
  - ts_headline with <mark> wrapping for UI highlight rendering
  - All 5 phase-3 endpoints verified end-to-end

affects:
  - frontend (search UI will consume /api/search response shape)
  - 04-frontend (if planned: search page, highlight rendering)

tech-stack:
  added: []
  patterns:
    - "Raw SQL via db.execute(sql`...`) for complex FTS queries that exceed Drizzle query builder"
    - "websearch_to_tsquery over to_tsquery for safe unescaped user input"
    - "count(*) OVER() window function for single-query pagination total"
    - "Optional filter clauses composed as sql template fragments, concatenated in WHERE"

key-files:
  created:
    - server/api/search.get.ts
  modified: []

key-decisions:
  - "Use db.execute(sql`...`) for FTS query — Drizzle query builder cannot express ts_rank, ts_headline, and multiple optional WHERE fragments cleanly"
  - "websearch_to_tsquery instead of to_tsquery — handles user input safely without manual escaping"
  - "Highlight options: MaxFragments=2 with ... delimiter for multi-excerpt snippets"

patterns-established:
  - "Optional filter composition: build sql`` fragment (empty or real clause), concatenate in main query"
  - "Error re-throw pattern: check .statusCode to distinguish H3 errors from DB errors"

duration: 3min
completed: 2026-03-27
---

# Phase 3 Plan 03: Full-Text Search Endpoint Summary

**PostgreSQL FTS endpoint using websearch_to_tsquery('french') with ts_rank ordering and ts_headline `<mark>` highlighting, filtered by deputyId/debateId/tag**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-27T22:39:25Z
- **Completed:** 2026-03-27T22:42:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- GET /api/search returns ranked French FTS results against 8402+ interventions
- Highlights wrap matched terms in `<mark>` tags (ts_headline with MaxFragments=2)
- Three optional filters: deputyId, debateId, tag slug — all verified working
- All 5 phase-3 endpoints smoke-tested and confirmed functional with correct edge case handling

## Task Commits

1. **Task 1: Full-text search endpoint** - `588bcf6` (feat)
2. **Task 2: API smoke tests and env verification** - no code changes (all endpoints working, no fixes needed)

## Files Created/Modified

- `server/api/search.get.ts` — GET /api/search with FTS, filters, ranking, highlights, pagination

## Decisions Made

- Used `db.execute(sql\`...\`)` rather than Drizzle query builder — FTS functions (ts_rank, ts_headline, websearch_to_tsquery) and optional WHERE fragment composition require raw SQL for clarity and correctness
- Chose `websearch_to_tsquery` over `to_tsquery` — handles unescaped user input safely (no need to pre-process special characters)
- Optional filters built as empty or populated `sql\`\`` fragments, concatenated directly — avoids conditional query-builder branching

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — NUXT_DATABASE_URL was already set, GIN index on interventions.content was already in schema, all dependencies available.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All 5 phase-3 API endpoints operational: /api/health, /api/debates, /api/debates/:id, /api/deputies, /api/deputies/:id, /api/search
- FTS index (GIN on to_tsvector('french', content)) confirmed working via query execution
- Search response shape stable: { data: [...], pagination: { page, limit, total, totalPages } }
- Phase 3 complete — ready for frontend phase

---
*Phase: 03-api-backend*
*Completed: 2026-03-27*
