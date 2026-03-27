---
phase: 04-ui-debats-thread-view
plan: 03
subsystem: ui
tags: [vue, nuxt, tailwind, debate-thread, routing]

# Dependency graph
requires:
  - phase: 04-01
    provides: InterventionCard, GroupBadge, LoadingSpinner components
  - phase: 03-01
    provides: GET /api/debates/:id endpoint (debate + enriched interventions)
provides:
  - Dynamic route page /debates/[id] — debate thread view
affects:
  - Home page (04-02 index.vue DebateCard links to this route)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "definePageMeta with validate for route param type safety"
    - "useFetch with template literal route — returns { debate, interventions }"
    - "v-bind spread on InterventionCard to pass all props from API response"
    - "useHead with computed title for reactive SEO"
    - "Intl.DateTimeFormat with explicit fr-FR locale + Europe/Paris timezone (SSR-safe)"

key-files:
  created:
    - app/pages/debates/[id].vue
  modified: []

key-decisions:
  - "No virtual scrolling — browser handles 1000 simple nodes fine; premature optimization deferred"
  - "v-bind spread on InterventionCard instead of individual prop binding — API shape matches component props"
  - "Optional chaining throughout template (data?.debate, data?.interventions) — null-safe during loading"

# Metrics
duration: ~5min
completed: 2026-03-28
---

# Phase 4 Plan 03: Debate Thread Page Summary

**Dynamic route /debates/[id] rendering all interventions as a Twitter-style thread via InterventionCard, with route validation, SEO title, and full error/loading/empty state handling**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-27T23:07:17Z
- **Completed:** 2026-03-27T23:08:08Z (Task 1) — awaiting human verify checkpoint
- **Tasks:** 1/2 complete (checkpoint:human-verify pending)
- **Files modified:** 1

## Accomplishments

- Created `app/pages/debates/[id].vue` — Nuxt 4 dynamic route page
- `definePageMeta` with `validate` ensures route param is a positive integer (`/^\d+$/`)
- `useFetch` loads `/api/debates/${id}` which returns `{ debate, interventions }` in one call
- `useHead` with computed title: `debate.title + ' — Poliscope'`
- Thread body renders all interventions using `<InterventionCard v-for v-bind="intervention" />` — spreads all props the component expects
- Page header: back link `← Retour aux debats`, h1 title, formatted date (fr-FR / Europe/Paris), intervention count
- States handled: loading (LoadingSpinner), 404 error ("Debat introuvable"), generic error, empty interventions list

## Task Commits

1. **Task 1: Debate thread page** — `b93b901` (feat)

## Files Created/Modified

- `app/pages/debates/[id].vue` — Dynamic debate thread page (73 lines)

## Decisions Made

- No virtual scrolling added — plan explicitly deferred this as premature optimization; browser handles ~1000 simple nodes
- `v-bind` spread used on `InterventionCard` — API response shape matches component prop interface exactly (id, speakerName, speakerRole, content, orderInDebate, deputy, tags)
- Optional chaining on all `data.value` accesses in template — null-safe during SSR and pending state

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `app/pages/debates/[id].vue` exists (73 lines, > 50 min)
- [x] Uses `useFetch` with route param
- [x] Uses `<InterventionCard`
- [x] Has `definePageMeta` with `validate`
- [x] Has `useHead`
- [x] Commit `b93b901` exists

## Self-Check: PASSED

## Issues Encountered

None.

## Next Phase Readiness

- Checkpoint human-verify pending — user must start dev server and visually verify both /debates/:id (this plan) and / (04-02, which must also be complete)
- After checkpoint approval, phase 4 is complete

---
*Phase: 04-ui-debats-thread-view*
*Completed: 2026-03-28 (partial — checkpoint pending)*
