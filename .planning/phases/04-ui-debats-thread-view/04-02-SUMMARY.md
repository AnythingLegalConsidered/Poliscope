---
phase: 04-ui-debats-thread-view
plan: 02
subsystem: ui
tags: [vue, nuxt, tailwind, vueuse, infinite-scroll, intersection-observer]

# Dependency graph
requires:
  - phase: 04-01
    provides: LoadingSpinner component used in home page loading state
  - phase: 03-01
    provides: GET /api/debates endpoint with paginated response shape (data[], pagination.totalPages)
provides:
  - Home page with paginated debates list and infinite scroll (app/pages/index.vue)
  - Reusable DebateCard component for debate list items (app/components/DebateCard.vue)
affects:
  - 04-03 debate thread page (uses same DebateCard navigation pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useIntersectionObserver sentinel pattern for infinite scroll (rootMargin: 200px)"
    - "useFetch with reactive ref in watch option — automatic re-fetch on page change, no manual refresh()"
    - "Accumulated list pattern: allDebates.ref accumulates across pages via watch(data, ..., { immediate: true })"
    - "useTemplateRef('sentinel') for Nuxt 4 / Vue 3.5+ template ref pattern"
    - "Intl.DateTimeFormat with explicit locale + timezone in computed — avoids SSR/client hydration mismatch"

key-files:
  created:
    - app/components/DebateCard.vue
  modified:
    - app/pages/index.vue

key-decisions:
  - "Date formatted in computed (not inline template) with explicit fr-FR locale and Europe/Paris timezone — prevents SSR hydration mismatch"
  - "watch(data, ..., { immediate: true }) captures SSR-hydrated initial data without extra fetch"
  - "useFetch watch: [page] re-fetches automatically — no manual refresh() call needed"

patterns-established:
  - "Infinite scroll sentinel: <div ref='sentinel' class='h-1' aria-hidden='true'> at list bottom, observed with 200px rootMargin"
  - "Double-trigger guard: check status.value !== 'pending' before incrementing page in observer callback"
  - "allDebates accumulator: start empty, push new pages in, never reset (persistent scroll history)"

# Metrics
duration: ~2min
completed: 2026-03-28
---

# Phase 4 Plan 02: Debates List Page Summary

**Home page with SSR-rendered DebateCard grid and useIntersectionObserver infinite scroll loading 20 debates per page from /api/debates**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-27T23:06:50Z
- **Completed:** 2026-03-27T23:08:16Z
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- Created `DebateCard.vue` — full-card NuxtLink to /debates/:id, title with line-clamp-2, French-formatted date in computed, session type badge, legislature label
- Rewrote `index.vue` — SSR-rendered first page via useFetch, infinite scroll via useIntersectionObserver on sentinel div with 200px pre-load margin, accumulated allDebates list across pages
- Verified live: SSR produces 20 debate cards on first load (257 total, 13 pages), dates correctly formatted as "26 janvier 2026"

## Task Commits

Each task was committed atomically:

1. **Task 1: DebateCard component** - `9fb6a35` (feat)
2. **Task 2: Home page with infinite scroll** - `f3cde7a` (feat)

## Files Created/Modified
- `app/components/DebateCard.vue` - Debate list card: NuxtLink, title, fr-FR date, session type badge, legislature label (43 lines)
- `app/pages/index.vue` - Home page: useFetch + reactive page, allDebates accumulator, useIntersectionObserver sentinel, responsive grid (91 lines)

## Decisions Made
- Date formatting done in `computed` with explicit `'fr-FR'` locale and `'Europe/Paris'` timezone — computed props are SSR-safe because they always produce the same output regardless of runtime environment, preventing hydration mismatches
- `watch: [page]` on useFetch handles re-fetching automatically, so no `refresh()` call needed — cleaner and avoids double-fetch bugs
- `{ immediate: true }` on the data watcher ensures SSR-hydrated first page is captured into allDebates without waiting for the next page navigation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Home page SSR-renders debates list immediately on load
- DebateCard links to /debates/:id — ready to implement debate thread page (04-03)
- Infinite scroll works client-side via useIntersectionObserver
- Both components auto-imported by Nuxt 4 (placed in app/components/)

## Self-Check: PASSED

- app/components/DebateCard.vue: FOUND (43 lines, min 20)
- app/pages/index.vue: FOUND (91 lines, min 40)
- Commit 9fb6a35: FOUND
- Commit f3cde7a: FOUND

---
*Phase: 04-ui-debats-thread-view*
*Completed: 2026-03-28*
