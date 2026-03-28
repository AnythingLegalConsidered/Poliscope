---
phase: 05-profils-deputes
plan: 01
subsystem: ui
tags: [nuxt, vue, vueuse, tailwindcss, infinite-scroll, deputies]

requires:
  - phase: 03-api-endpoints
    provides: GET /api/deputies with search/group filter, paginated response
  - phase: 04-ui-debats
    provides: GroupBadge, LoadingSpinner, DebateCard pattern, design tokens, useIntersectionObserver pattern

provides:
  - DeputyCard component (photo/initials, name, group badge, constituency, NuxtLink to /deputies/:id)
  - Deputies list page at /deputies (search, group filter dropdown, infinite scroll)
  - "Députés" nav link in header layout with active-class highlighting

affects: [05-02-profils-deputes]

tech-stack:
  added: []
  patterns:
    - "Deputies list page mirrors index.vue: useFetch + useIntersectionObserver + allDeputies accumulator"
    - "Filter reset pattern: watch([search, group]) sets allDeputies=[] and page=1 atomically"
    - "Page 1 replacement vs. push pattern in data watcher prevents duplicates on filter change"
    - "DeputyCard follows DebateCard structure: NuxtLink wrapper, parchment bg, bronze hover border"
    - "imageError ref + @error handler for photo fallback to initials"

key-files:
  created:
    - app/components/DeputyCard.vue
    - app/pages/deputies/index.vue
  modified:
    - app/layouts/default.vue
    - app/pages/index.vue
    - server/api/debates/index.get.ts
    - server/api/deputies/index.get.ts
    - server/api/deputies/[id].get.ts
    - server/api/search.get.ts

key-decisions:
  - "Hardcoded 17th legislature groups list for filter dropdown (RN, EPR, LFI-NFP, SOC, DR, HOR, EcoS, LIOT, GDR, UDR, NI)"
  - "active-class='text-bronze' on NuxtLink (not router-link-active CSS) for active state"

patterns-established:
  - "DeputyCard: flex row layout, w-12 h-12 avatar, initials fallback with imageError ref"
  - "Deputies index: same infinite scroll pattern as debates index with added search/group filters"

duration: 12min
completed: 2026-03-28
---

# Phase 5 Plan 01: Deputies List Page Summary

**DeputyCard component + /deputies list page with search input, group filter dropdown, and infinite scroll mirroring the debates list pattern**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-28T00:40:07Z
- **Completed:** 2026-03-28T00:52:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- `DeputyCard.vue` — photo with @error initials fallback, NuxtLink to /deputies/:id, GroupBadge, constituency
- `deputies/index.vue` — search input, 11-group dropdown filter, infinite scroll (useIntersectionObserver), empty state, "Tous les députés chargés" end message
- "Députés" nav link added to header with active-class="text-bronze" highlighting

## Task Commits

Each task was committed atomically:

1. **Task 1: DeputyCard + deputies list page** - `b8bcd24` (feat)
2. **Task 2: Add Députés nav link to header** - `b5cae9b` (feat)

## Files Created/Modified
- `app/components/DeputyCard.vue` - Deputy card: photo/initials, name, constituency, GroupBadge, NuxtLink
- `app/pages/deputies/index.vue` - Deputies list: search, group filter, infinite scroll, loading/empty states
- `app/layouts/default.vue` - Added Députés NuxtLink after Débats in nav
- `app/pages/index.vue` - Fixed pre-existing `entry?.isIntersecting` optional chaining (TS18048)
- `server/api/debates/index.get.ts` - Fixed `.at(0)` pattern for totalCount (TS2532)
- `server/api/deputies/index.get.ts` - Fixed `.at(0)` pattern for totalCount (TS2532)
- `server/api/deputies/[id].get.ts` - Fixed `.at(0)` pattern for totalCount (TS2532)
- `server/api/search.get.ts` - Fixed `.at(0)` pattern for total_count (TS2532)

## Decisions Made
- Hardcoded the 17th legislature group list for the filter dropdown (RN, EPR, LFI-NFP, SOC, DR, HOR, EcoS, LIOT, GDR, UDR, NI) — simpler than extracting from loaded data, stable for the current legislature
- Used `active-class="text-bronze"` prop on NuxtLink (not global CSS) for active nav highlighting

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed optional chaining on IntersectionObserver entry (TS18048)**
- **Found during:** Task 1 typecheck
- **Issue:** `entry.isIntersecting` in deputies/index.vue and index.vue — TS flagged `entry` as possibly undefined
- **Fix:** Changed to `entry?.isIntersecting` in both files
- **Files modified:** `app/pages/deputies/index.vue`, `app/pages/index.vue`
- **Verification:** `npx nuxi typecheck` passes with 0 errors
- **Committed in:** b8bcd24 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed array indexing `rows[0]` replaced with `.at(0)` pattern (TS2532)**
- **Found during:** Task 1 typecheck
- **Issue:** 4 server API files used `rows[0].totalCount` guarded by `rows.length > 0` — TS doesn't narrow this in ternary, flags `rows[0]` as possibly undefined
- **Fix:** Changed to `Number(rows.at(0)?.totalCount ?? 0)` — equivalent logic, type-safe
- **Files modified:** `server/api/debates/index.get.ts`, `server/api/deputies/index.get.ts`, `server/api/deputies/[id].get.ts`, `server/api/search.get.ts`
- **Verification:** `npx nuxi typecheck` passes with 0 errors
- **Committed in:** b8bcd24 (Task 1 commit)

**3. [Rule 1 - Bug] Regenerated Nuxt types to fix InterventionCard TS2345 mismatch**
- **Found during:** Task 1 typecheck
- **Issue:** `debates/[id].vue` v-bind spread failed type check against stale `InterventionCard` types (missing `deputyId` prop in generated types)
- **Fix:** Ran `npx nuxi prepare` to regenerate `.nuxt/` type declarations
- **Files modified:** `.nuxt/` (generated, not committed)
- **Verification:** TS2345 error gone after prepare
- **Committed in:** b8bcd24 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (3 × Rule 1 — bug fixes, all pre-existing type errors)
**Impact on plan:** All auto-fixes necessary for correctness. Zero type errors at completion. No scope creep.

## Issues Encountered
- Plans 05-02 commits already existed (`2ce1d8d`, `f7492b4`) before 05-01 was executed — the `InterventionCard.vue` update was already committed. This plan was executed after 05-02 ran in a prior session. No conflict — 05-01 files did not overlap with 05-02 files.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `/deputies` list page is fully functional — ready for plan 05-02 (deputy profile page) which already has commits
- `DeputyCard` links to `/deputies/:id` — profile page is already implemented in prior session commits
- All type errors cleared — codebase is type-clean

---
*Phase: 05-profils-deputes*
*Completed: 2026-03-28*
