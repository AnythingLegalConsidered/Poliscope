---
phase: 04-ui-debats-thread-view
plan: 01
subsystem: ui
tags: [vue, nuxt, tailwind, vueuse, political-groups]

# Dependency graph
requires:
  - phase: 03-api-backend
    provides: API response shape from /api/debates/[id] used to define InterventionCard props
provides:
  - Reusable GroupBadge component (colored political group pill)
  - Reusable InterventionCard component (thread-style debate post)
  - Reusable LoadingSpinner component
  - groupColors utility with all 11 French political group colors
affects:
  - 04-02 debates list page (uses InterventionCard, GroupBadge, LoadingSpinner)
  - 04-03 debate thread page (uses InterventionCard, GroupBadge, LoadingSpinner)

# Tech tracking
tech-stack:
  added: ["@vueuse/core@14.2.1"]
  patterns:
    - "Auto-imported utils via app/utils/ (Nuxt 4 convention)"
    - "Auto-imported components via app/components/ (Nuxt 4 convention)"
    - "Inline styles for dynamic per-group colors (not CSS variables)"
    - "Optional chaining for nullable deputy prop throughout InterventionCard"

key-files:
  created:
    - app/utils/groupColors.ts
    - app/components/GroupBadge.vue
    - app/components/InterventionCard.vue
    - app/components/LoadingSpinner.vue
  modified:
    - app/assets/css/main.css
    - package.json

key-decisions:
  - "Group colors via inline JS (getGroupColor) rather than CSS variables — avoids unused rules for dynamic data"
  - "InterventionCard uses whitespace-pre-wrap instead of v-html — safe, handles multiline content"
  - "GroupBadge renders nothing (v-if) for null group — ministers/president have no group"

patterns-established:
  - "Nullable deputy pattern: all deputy access via optional chaining (deputy?.fullName, deputy?.photoUrl, deputy?.group)"
  - "Avatar fallback: photo URL when available, else initials div with bg-primary background"
  - "Group color system: getGroupColor(group) returns hex, fallback #6b7280 for null/unknown"

# Metrics
duration: 8min
completed: 2026-03-28
---

# Phase 4 Plan 01: Shared UI Components Summary

**@vueuse/core installed plus 3 thread-view components and an 11-group French political color system with null-safe deputy handling**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-27T23:02:57Z
- **Completed:** 2026-03-27T23:10:00Z
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments
- Installed @vueuse/core for use in upcoming page components
- Created `groupColors.ts` with `getGroupColor` / `getGroupLabel` covering all 11 DB group values (LFI, GDR, SOC, ECO, LIOT, MODEM, REN, HOR, LR, RN, NI) plus null fallback
- Built `GroupBadge.vue` — colored pill badge using inline style from `getGroupColor`, hides when group is null
- Built `InterventionCard.vue` — Twitter-thread-style post with photo/initials avatar, speaker name, group badge, role, and content (whitespace-pre-wrap, no v-html); fully null-safe for deputy
- Built `LoadingSpinner.vue` — centered animated SVG spinner with text-primary color

## Task Commits

Each task was committed atomically:

1. **Task 1: Install @vueuse/core + group color system** - `2e896ad` (feat)
2. **Task 2: Build GroupBadge, InterventionCard, LoadingSpinner** - `5418968` (feat)

## Files Created/Modified
- `app/utils/groupColors.ts` - Group acronym to hex color and full label mapping, getGroupColor/getGroupLabel exports
- `app/components/GroupBadge.vue` - Political group colored pill badge (19 lines)
- `app/components/InterventionCard.vue` - Thread-style debate post component (66 lines)
- `app/components/LoadingSpinner.vue` - Reusable animated loading indicator (24 lines)
- `app/assets/css/main.css` - Added comment explaining group colors are JS-driven
- `package.json` - Added @vueuse/core dependency

## Decisions Made
- Group colors implemented via inline JS styles rather than CSS custom properties — dynamic data makes static CSS variables wasteful and inflexible
- `whitespace-pre-wrap` used in InterventionCard content instead of `v-html` — XSS-safe, handles line breaks in debate transcript text
- `GroupBadge` renders nothing for null group — consistent with ministers and the president who have no political group affiliation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 3 shared components auto-importable by Nuxt 4 (placed in app/components/)
- `groupColors.ts` auto-importable by Nuxt 4 (placed in app/utils/)
- @vueuse/core available for use in composables and page components
- Ready to build 04-02 (debates list page) and 04-03 (debate thread page)

---
*Phase: 04-ui-debats-thread-view*
*Completed: 2026-03-28*
