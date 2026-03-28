---
phase: 06-recherche-filtres
plan: 02
subsystem: ui
tags: [nuxt, vue, tailwindcss, search, layout]

# Dependency graph
requires:
  - phase: 06-01
    provides: /search page with FTS highlights, tag filter, infinite scroll, URL-synced state
  - phase: 04-ui-debates
    provides: Marbre & Bronze design system, default.vue layout baseline
provides:
  - Global search bar in header (all pages) navigating to /search?q=...
  - "Recherche" nav link in header
  - End-to-end search experience verified via Playwright (10/10 tests passing)
affects: [future search enhancements, header layout changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Compact header search input: form @submit.prevent + navigateTo + ref clear after nav
    - Parchment/stone-border/bronze-focus input styling matching Marbre & Bronze system

key-files:
  created: []
  modified:
    - app/layouts/default.vue
    - app/components/SearchResultCard.vue

key-decisions:
  - "NuxtLink resolution fix in SearchResultCard committed as part of this plan's verification pass"
  - "Immediate fetch on URL load added as bug fix during checkpoint verification"

patterns-established:
  - "Header search: hidden on xs, w-48 on sm+, clear input after navigateTo"

# Metrics
duration: ~15min
completed: 2026-03-28
---

# Phase 6 Plan 02: Global Header Search Bar Summary

**Compact search input added to default layout header — navigates to /search?q=... from any page, fully verified end-to-end via 10 Playwright automated tests (highlights, infinite scroll, tag filter, URL sharing, empty states)**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-03-28
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 2

## Accomplishments

- Added compact search input to `default.vue` header with Marbre & Bronze styling (parchment bg, stone border, bronze focus ring)
- Form submit navigates to `/search?q=...` via `navigateTo`, clears input after navigation
- Fixed `NuxtLink` resolution issue in `SearchResultCard` and immediate fetch on URL load (bug fixes discovered during checkpoint verification)
- Full search experience verified via Playwright: 10/10 tests passed covering highlights, infinite scroll, tag filter, URL sharing, and empty/no-results states

## Task Commits

1. **Task 1: Add search bar to header layout** - `85a1d88` (feat)
2. **Post-checkpoint fixes: NuxtLink resolution + immediate fetch** - `64a5e09` (fix)

## Files Created/Modified

- `app/layouts/default.vue` — Added `headerSearch` ref, form with `@submit.prevent`, `navigateTo` call, Marbre & Bronze input styling, hidden on xs / w-48 on sm+
- `app/components/SearchResultCard.vue` — Fixed `NuxtLink` component resolution (was failing silently)

## Decisions Made

- **NuxtLink fix classified as bug (Rule 1):** `SearchResultCard` was not resolving `NuxtLink` correctly — fixed inline as part of checkpoint verification without scope change.
- **Immediate fetch on URL load:** When `/search` is loaded with `?q=...` in the URL, fetch was not triggering on mount — fixed to ensure shared URLs work correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NuxtLink not resolving in SearchResultCard**
- **Found during:** Task 2 (human-verify checkpoint — Playwright test run)
- **Issue:** `NuxtLink` component was not resolving correctly inside `SearchResultCard`, breaking deputy and debate navigation links
- **Fix:** Corrected NuxtLink usage in the component
- **Files modified:** `app/components/SearchResultCard.vue`
- **Committed in:** `64a5e09` (post-checkpoint fix)

**2. [Rule 1 - Bug] No immediate fetch when /search loaded with URL params**
- **Found during:** Task 2 (human-verify checkpoint — test 8: shared URL)
- **Issue:** Navigating to `/search?q=immigration` directly did not trigger the initial fetch, showing empty results
- **Fix:** Added immediate fetch trigger on mount when `q` is present in `route.query`
- **Files modified:** `app/pages/search.vue`
- **Committed in:** `64a5e09` (post-checkpoint fix)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes necessary for correct UX. No scope creep.

## Issues Encountered

Playwright automated testing (10 tests) surfaced two bugs during the checkpoint verification phase. Both were fixed and re-verified before approval.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 6 complete — both plans done (06-01 + 06-02)
- Full search experience operational: header search → /search → FTS highlights → tag filter → infinite scroll → URL sharing
- Phase 6 success criteria met: "On peut chercher 'immigration' et trouver toutes les interventions sur le sujet"
- Ready for Milestone 1 completion review or next milestone planning

## Self-Check: PASSED

- app/layouts/default.vue — FOUND (via plan artifact)
- app/components/SearchResultCard.vue — FOUND (via plan artifact)
- 06-02-SUMMARY.md — this file
- Commit 85a1d88 — FOUND
- Commit 64a5e09 — FOUND

---
*Phase: 06-recherche-filtres*
*Completed: 2026-03-28*
