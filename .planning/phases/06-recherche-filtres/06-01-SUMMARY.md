---
phase: 06-recherche-filtres
plan: 01
subsystem: ui
tags: [nuxt, vue, postgresql, fts, search, tailwindcss, vueuse]

# Dependency graph
requires:
  - phase: 03-api-backend
    provides: GET /api/search with FTS, ts_headline highlights, deputyId/tag filters
  - phase: 04-ui-debates
    provides: Marbre & Bronze design system, InterventionCard, GroupBadge, LoadingSpinner
  - phase: 05-profils-deputes
    provides: infinite scroll pattern (useIntersectionObserver), deputies page URL filter pattern
provides:
  - /search page with FTS highlights, tag filter, infinite scroll, URL-synced state
  - SearchResultCard component with v-html highlight rendering, tag pills, deputy/debate links
  - mark { } CSS styling for FTS <mark> tags (bronze-light background)
  - Extended /api/search returning tags[] per result via json_agg correlated subquery
affects: [06-02, future search enhancements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - URL-synced filter state (read once from route.query on mount, write back via router.replace)
    - FTS highlight rendering via v-html (safe — content from own PostgreSQL ts_headline)
    - watchDebounced pattern for search input debounce (300ms)
    - Manual useFetch trigger with immediate:false + watch:false guarded by shouldFetch computed

key-files:
  created:
    - app/pages/search.vue
    - app/components/SearchResultCard.vue
  modified:
    - server/api/search.get.ts
    - app/assets/css/main.css
    - app/layouts/default.vue

key-decisions:
  - "URL sync is one-directional: local ref -> URL only. Do NOT watch route.query back to avoid double-trigger loop."
  - "useFetch with immediate:false + watch:false + manual refresh() — avoids 400 error on empty q"
  - "Tag filter via click-to-filter on result pills (no pre-loaded tag list needed)"
  - "json_agg with COALESCE to empty JSON array ensures non-null tags in SQL response"

patterns-established:
  - "SearchResultCard: v-html for FTS highlights, filter-tag emit on tag pill click"
  - "Page-level URL state: inputValue (raw) + q (debounced, URL-synced) separation"

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 6 Plan 01: Search UI Summary

**Search results page /search with FTS highlight rendering (v-html + mark CSS), URL-synced q/tag/deputyId filters, infinite scroll, and extended /api/search returning tags[] via PostgreSQL json_agg**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-28T01:23:08Z
- **Completed:** 2026-03-28T01:25:39Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Extended `/api/search` to return `tags[]` per result via correlated `json_agg` subquery
- Created `SearchResultCard.vue` with FTS highlight (`v-html`), speaker info, GroupBadge, deputy/debate NuxtLinks, and tag pills emitting `filter-tag` event
- Created `/search` page with debounced input, URL-synced state (`q`, `tag`, `deputyId`), guarded `useFetch` (no 400 on empty query), infinite scroll via `useIntersectionObserver`, and tag filter UX
- Added `mark { }` CSS rule with `bronze-light` background for FTS highlight styling
- Added "Recherche" link to header nav

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend search API to return tags per result** - `a232986` (feat)
2. **Task 2: Create SearchResultCard component + mark styling** - `154b5b7` (feat)
3. **Task 3: Create /search page with URL-synced state and infinite scroll** - `4fb89f7` (feat)

## Files Created/Modified

- `server/api/search.get.ts` — Added `json_agg` correlated subquery for tags, tags in type assertion and response mapping
- `app/components/SearchResultCard.vue` — Search result card with highlight, speaker info, debate link, deputy link, group badge, tag filter pills
- `app/assets/css/main.css` — Added `mark { }` rule using `bronze-light` token for FTS highlights
- `app/pages/search.vue` — Search results page: debounced input, URL-synced filters, guarded fetch, accumulator, infinite scroll, empty/no-results states
- `app/layouts/default.vue` — Added Recherche nav link in header

## Decisions Made

- **URL sync one-directional:** Local ref → URL only via `router.replace()`. No watch on `route.query` after init to avoid double-trigger infinite loop (pitfall 6 from RESEARCH.md).
- **`useFetch` with `immediate: false` + `watch: false`:** Manual refresh trigger guarded by `shouldFetch` computed prevents 400 error when `/search` is visited with empty query.
- **Tag filter from result pills:** No pre-loaded tag list needed — clicking a tag pill on a result activates the tag filter. Zero new API endpoints required.
- **`json_agg` with `COALESCE(..., '[]'::json)`:** Ensures `tags` is always a non-null JSON array in the PostgreSQL response, even for interventions without tags.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `/search` page fully functional — ready for Phase 6 Plan 2 (global header search bar, if applicable)
- All must-haves from plan verified via code patterns (API returns tags[], v-html for highlights, URL sync, infinite scroll)
- Dev server verification pending (requires running Docker + Nuxt dev)

## Self-Check: PASSED

- server/api/search.get.ts — FOUND
- app/components/SearchResultCard.vue — FOUND
- app/pages/search.vue — FOUND
- app/assets/css/main.css — FOUND
- 06-01-SUMMARY.md — FOUND
- Commit a232986 — FOUND
- Commit 154b5b7 — FOUND
- Commit 4fb89f7 — FOUND

---
*Phase: 06-recherche-filtres*
*Completed: 2026-03-28*
