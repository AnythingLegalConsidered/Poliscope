---
phase: 05-profils-deputes
plan: 02
subsystem: ui
tags: [vue, nuxt, deputies, profile, pagination, tag-filter, bidirectional-navigation]

requires:
  - phase: 05-01
    provides: Deputies list page + DeputyCard component
  - phase: 03-02
    provides: GET /api/deputies/:id with tagStats and paginated interventions
  - phase: 04-01
    provides: InterventionCard, GroupBadge, LoadingSpinner components

provides:
  - Deputy profile page at /deputies/:id with header, tag filter pills, paginated intervention list
  - Bidirectional navigation between deputy profiles and debate threads
  - InterventionCard with optional deputyId prop enabling profile links

affects:
  - Future phases using InterventionCard (deputyId prop is now part of the interface)
  - Any page adding InterventionCard with v-bind spread from APIs that return deputyId

tech-stack:
  added: []
  patterns:
    - allInterventions accumulator with watch(data, immediate) — same pattern as allDebates in index.vue
    - component :is pattern for conditionally rendering NuxtLink vs div (avatar clickability)
    - Client-side tag filter on accumulated loaded interventions (not server-side)

key-files:
  created:
    - app/pages/deputies/[id].vue
  modified:
    - app/components/InterventionCard.vue
    - app/pages/index.vue (auto-fix: optional chaining on entry)

key-decisions:
  - "deputyId is optional prop on InterventionCard — existing v-bind spreads auto-pass it since API already returns it"
  - "Tag filter is client-side on allInterventions — simpler UX, resets on new page load"
  - "Accumulation pattern (not replace-on-page) for load-more UX consistent with deputies/index.vue"
  - "Deputy.fullName typed as string | null to match API SerializeObject<> shape (was pre-existing mismatch)"

patterns-established:
  - "Profile page: back link → header section → stats section → filtered list → pagination"
  - "Conditional NuxtLink wrapper via :is for clickable avatars/names without prop drilling"

duration: 18min
completed: 2026-03-28
---

# Phase 05 Plan 02: Deputy Profile Page Summary

**Deputy profile page at /deputies/:id with photo header, clickable tag stats, accumulated+filtered interventions list with debate context links, and bidirectional navigation via updated InterventionCard deputyId prop.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-28T00:40:07Z
- **Completed:** 2026-03-28T00:58:00Z
- **Tasks:** 2/2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Deputy profile page with photo avatar (+ initials fallback with `@error` handler), name, GroupBadge, constituency, and intervention count
- Top-10 tag pills with toggle active state (bronze border) for client-side filtering across all loaded interventions
- Load more button accumulating interventions across pages (consistent with `allDebates`/`allDeputies` pattern)
- Each intervention shows debate context as NuxtLink above the InterventionCard
- InterventionCard now renders deputy name and avatar as clickable links to `/deputies/:id` when `deputyId` is present; non-deputy speakers unaffected

## Task Commits

1. **Task 1: Deputy profile page** — `2ce1d8d` (feat)
2. **Task 2: InterventionCard deputyId prop + bidirectional nav** — `f7492b4` (feat)

## Files Created/Modified

- `app/pages/deputies/[id].vue` — Deputy profile page (created)
- `app/components/InterventionCard.vue` — Added `deputyId` optional prop, conditional NuxtLink for name and avatar
- `app/pages/index.vue` — Auto-fix: `entry?.isIntersecting` optional chaining (Rule 1 - bug)

## Decisions Made

- `deputyId` is optional (`?`) on InterventionCard so all existing `v-bind` spreads on debate thread pages work without changes — the API already returns `deputyId` in intervention objects so it passes through automatically
- Tag filter resets `activeTag` to null when `page` increments (not on data change) to avoid confusion when filter was active and more pages load
- Used `component :is` pattern for clickable avatars — cleaner than duplicating entire avatar markup in `v-if`/`v-else` blocks
- Fixed `Deputy.fullName` type from `string` to `string | null` to match the actual Drizzle/Nuxt `SerializeObject<>` shape — this resolved a pre-existing TS2345 error on `debates/[id].vue`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `Deputy.fullName: string | null` type mismatch in InterventionCard**
- **Found during:** Task 2 (typecheck verification)
- **Issue:** InterventionCard declared `Deputy.fullName: string` but the API returns `fullName: string | null` (Drizzle column is nullable). TypeScript was rejecting `v-bind` spreads in `debates/[id].vue` with TS2345.
- **Fix:** Changed `fullName: string` to `fullName: string | null` in InterventionCard's local `Deputy` interface; updated `displayName` computed to add `?? ''` fallback
- **Files modified:** `app/components/InterventionCard.vue`
- **Verification:** TS2345 error on debates/[id].vue resolved in next typecheck run
- **Committed in:** `f7492b4` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed `entry` possibly undefined in index.vue IntersectionObserver callback**
- **Found during:** Task 2 (typecheck run)
- **Issue:** `[entry]` destructuring in `useIntersectionObserver` callback — `entry` typed as possibly `undefined` (TS18048). `entry.isIntersecting` would throw at runtime if array was empty.
- **Fix:** Changed `entry.isIntersecting` to `entry?.isIntersecting` (optional chaining)
- **Files modified:** `app/pages/index.vue`
- **Verification:** Error removed from typecheck output
- **Committed in:** `f7492b4` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - pre-existing bugs surfaced by typecheck)
**Impact on plan:** Both fixes necessary for type correctness and runtime safety. No scope creep.

## Issues Encountered

- Typecheck runner (`npx nuxi typecheck`) uses a cached version of `vue-tsc` from npm cache that cannot find `@vue/language-core` from the project's local `node_modules`. This causes a `[Vue] Resolve plugin path failed` warning at the top of every typecheck run, but does not affect the actual TypeScript error detection. Remaining errors in `server/api/*.ts` (TS2532 `Object is possibly undefined`) are pre-existing and not introduced by this plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Deputy profile page is complete and functional
- Phase 05 (profils-deputes) is now complete: deputies list (05-01) + deputy profile (05-02)
- Bidirectional navigation between debate threads and deputy profiles is fully implemented
- Ready for Phase 06 if planned (search UI, statistics, etc.)

---
*Phase: 05-profils-deputes*
*Completed: 2026-03-28*
