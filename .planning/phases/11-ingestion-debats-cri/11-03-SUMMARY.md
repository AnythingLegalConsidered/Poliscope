---
phase: 11-ingestion-debats-cri
plan: 03
subsystem: web-frontend + api
tags: [chamber-filter, ui, debates, api]
dependency_graph:
  requires: [11-01, 11-02]
  provides: [chamber-filtered-debates-api, chamber-selector-ui]
  affects: [packages/web/server/api/debates/index.get.ts, packages/web/app/pages/index.vue, packages/web/app/components/DebateCard.vue]
tech_stack:
  added: []
  patterns: [drizzle-orm eq/and conditions array, useFetch reactive query param, computed page title, IntersectionObserver reset on filter change]
key_files:
  modified:
    - packages/web/server/api/debates/index.get.ts
    - packages/web/app/pages/index.vue
    - packages/web/app/components/DebateCard.vue
decisions: []
metrics:
  duration: ~15min
  completed: 2026-03-30
---

# Phase 11 Plan 03: Chamber Filter — API + UI Summary

**One-liner:** `?chamber=AN|Senat` filter on /api/debates with 3-tab selector UI and per-card chamber badge.

## What Was Built

### Task 1 — /api/debates chamber filter (commit `66d4256`)

Refactored `packages/web/server/api/debates/index.get.ts` following the exact same pattern as `deputies/index.get.ts`:

- Added `eq`, `and` imports from `drizzle-orm` and `SQL` type
- Reads `?chamber=AN|Senat` from query params — only accepts those two exact values (Rule 2 validation)
- Builds `conditions: SQL[]` array, pushes `eq(debates.chamber, chamber)` when valid
- Applies `.where(conditions.length > 0 ? and(...conditions) : undefined)` — no WHERE when filter absent
- Added `chamber: debates.chamber` to the SELECT so frontend receives the field

### Task 2 — Chamber selector UI + DebateCard badge (commit `d252cfa`)

**DebateCard.vue:**
- Added `chamber: string | null` to `defineProps`
- Bronze badge (`bg-bronze/10 text-bronze`) for AN debates
- Ink badge (`bg-ink/10 text-ink`) for Sénat debates
- Both badges placed in the bottom-left flex area alongside sessionType

**index.vue:**
- `chamber = ref<string | undefined>(undefined)` — undefined = all chambers
- `pageTitle` computed: "Débats de l'Assemblée nationale" / "Débats du Sénat" / "Débats parlementaires"
- 3 filter tabs (Tous / Assemblée nationale / Sénat) with active/inactive bronze styling
- `selectChamber(newVal)`: resets `page.value = 1`, clears `allDebates.value = []`, then sets `chamber.value` — ensures infinite scroll restarts from page 1
- `watch: [page, chamber]` in useFetch so filter changes trigger re-fetch
- Updated seoMeta description to generic "Les derniers débats parlementaires"
- `:chamber="debate.chamber"` passed to DebateCard

## Verification Results

| Check | Result |
|-------|--------|
| `grep -n "chamber" index.get.ts` | Shows eq + where usage |
| `grep -c "chamber" index.vue` | 12 matches |
| `grep -c "chamber" DebateCard.vue` | 3 matches |
| No hardcoded "Assemblée nationale" in h1 | PASS — uses `{{ pageTitle }}` |

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | `66d4256` | feat(11-03): add chamber filter to /api/debates endpoint |
| Task 2 | `d252cfa` | feat(11-03): add chamber selector UI and badge to debates list |

## Self-Check

Files exist:
- `packages/web/server/api/debates/index.get.ts` — FOUND
- `packages/web/app/pages/index.vue` — FOUND
- `packages/web/app/components/DebateCard.vue` — FOUND

Commits:
- `66d4256` — FOUND
- `d252cfa` — FOUND

## Self-Check: PASSED
