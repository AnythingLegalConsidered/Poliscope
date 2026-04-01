---
phase: 13-api-rest-universelle-openapi
plan: 02
subsystem: api
tags: [nuxt, h3, postgresql, openapi, scalar, full-text-search, union]

# Dependency graph
requires:
  - phase: 13-01
    provides: GET /api/votes, /api/deputies?chamber, voteStats on deputy profile
provides:
  - GET /api/search returning cross-type results (interventions + scrutins) with type discriminant
  - GET /api/docs — Scalar UI with all endpoints documented
  - GET /_openapi.json — OpenAPI 3.x spec for all 8 endpoints
  - Optional ?type=intervention|scrutin and ?chamber=AN|Senat filters on search
affects: [14-frontend-votes, frontend-search]

# Tech tracking
tech-stack:
  added:
    - "@scalar/nuxt ^0.6.18 — Scalar UI module for Nuxt"
  patterns:
    - "SQL UNION ALL wrapped in subquery: SELECT * FROM (branch1 UNION ALL branch2) sub — required for count(*) OVER() on combined result set"
    - "Batch tag fetch after UNION query: filter intervention IDs from results, then single inArray() query"
    - "defineRouteMeta at module top level (before export default) — Nitro OpenAPI annotation pattern"
    - "nitro.openAPI.production:'runtime' — mandatory for docs to work post-deployment"

key-files:
  modified:
    - packages/web/server/api/search.get.ts — Rewritten with UNION ALL + type/chamber filters + batch tags
    - packages/web/nuxt.config.ts — @scalar/nuxt module, nitro openAPI config, votes cache headers
    - packages/web/server/api/debates/index.get.ts — defineRouteMeta added
    - packages/web/server/api/debates/[id].get.ts — defineRouteMeta added
    - packages/web/server/api/deputies/index.get.ts — defineRouteMeta added
    - packages/web/server/api/deputies/[id].get.ts — defineRouteMeta added
    - packages/web/server/api/votes/index.get.ts — defineRouteMeta added
    - packages/web/server/api/votes/[id].get.ts — defineRouteMeta added
    - packages/web/server/api/health.get.ts — defineRouteMeta added
    - packages/web/package.json — @scalar/nuxt dependency added

key-decisions:
  - "SQL UNION ALL in subquery wrapper (not CTEs) — count(*) OVER() must be on outer query, not inside each branch"
  - "to_tsvector at query time for scrutins — 7k rows, no stored search_vector column, acceptable performance"
  - "Batch tag fetch post-UNION — correlated subquery inside UNION branch is complex; separate batch query simpler and avoids N+1"
  - "typeFilter determines which branches to include — if type=intervention, scrutins branch is skipped entirely (not filtered post-UNION)"
  - "production:'runtime' in nitro.openAPI — without this, /api/docs and /_openapi.json 404 in production builds"

# Metrics
duration: 12min
completed: 2026-04-01
---

# Phase 13 Plan 02: Cross-type Search + OpenAPI Summary

**SQL UNION ALL cross-type full-text search (interventions + scrutins) with type discriminant, plus @scalar/nuxt OpenAPI documentation on all 8 endpoints accessible at /api/docs**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-01T06:04:18Z
- **Completed:** 2026-04-01T06:16:00Z
- **Tasks:** 2
- **Files modified:** 10 (0 created, 10 modified)

## Accomplishments

- Rewrote `GET /api/search` with SQL UNION ALL approach: interventions branch uses stored `i.search_vector` (indexed), scrutins branch uses `to_tsvector` at query time on `s.title`
- Added `?type=intervention|scrutin` filter to restrict results to one type
- Added `?chamber=AN|Senat` filter applied independently to each branch
- Tags batch-fetched post-query for intervention results only (avoids N+1 inside UNION)
- All results carry a `type` discriminant field; intervention format backward compatible
- Installed `@scalar/nuxt` and configured Scalar UI at `/api/docs`
- OpenAPI spec at `/_openapi.json` with `production:'runtime'` for post-deploy availability
- Added `defineRouteMeta` to all 8 endpoint files (debates list/detail, deputies list/detail, votes list/detail, search, health)
- Added `/api/votes` and `/api/votes/**` cache headers to `nuxt.config.ts`
- Build verified: client + server both succeed with `@scalar/nuxt` resolved

## Task Commits

1. **Task 1: Extend search to cross-type FTS** - `a04804a` (feat)
2. **Task 2: Add OpenAPI metadata + Scalar UI** - `83020a4` (feat)

## Files Modified

- `packages/web/server/api/search.get.ts` — UNION ALL rewrite, type/chamber filters, batch tags, defineRouteMeta
- `packages/web/nuxt.config.ts` — @scalar/nuxt in modules, nitro openAPI config, votes routeRules
- `packages/web/server/api/debates/index.get.ts` — defineRouteMeta (tags, summary, params: chambre/page/limit)
- `packages/web/server/api/debates/[id].get.ts` — defineRouteMeta (tags, summary, params: id)
- `packages/web/server/api/deputies/index.get.ts` — defineRouteMeta (tags, summary, params: chamber/group/search/page/limit)
- `packages/web/server/api/deputies/[id].get.ts` — defineRouteMeta (tags, summary, params: id/page/limit)
- `packages/web/server/api/votes/index.get.ts` — defineRouteMeta (tags, summary, params: chambre/dateFrom/dateTo/result/page/limit)
- `packages/web/server/api/votes/[id].get.ts` — defineRouteMeta (tags, summary, params: id/position/page/limit)
- `packages/web/server/api/health.get.ts` — defineRouteMeta (tags: system, summary: Health check)
- `packages/web/package.json` + `pnpm-lock.yaml` — @scalar/nuxt dependency

## Decisions Made

- UNION branches assembled conditionally: if `?type=intervention`, scrutins branch is entirely skipped (not post-filtered) — more efficient
- `i.search_vector` used (stored, indexed) instead of `to_tsvector('french', i.content)` — performance improvement from existing code
- TypeScript peer warning from `@scalar/nuxt` (wants `^5.6.3`, found `6.0.2`) is non-blocking — package installed and build succeeds

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

- Phase 14 frontend can now consume `/api/search` for cross-type results with type-specific rendering
- `/api/docs` provides self-documenting API for any future consumer
- `/_openapi.json` enables automated client generation if needed
- Phase 13 complete — both plans executed

## Self-Check: PASSED

- All 10 files exist and verified
- Commits a04804a and 83020a4 confirmed in git log
- defineRouteMeta present in all 8 endpoint files (1 each)
- Build succeeded: client + server both completed without errors

---
*Phase: 13-api-rest-universelle-openapi*
*Completed: 2026-04-01*
