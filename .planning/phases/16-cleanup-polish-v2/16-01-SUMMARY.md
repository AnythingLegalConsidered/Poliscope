---
phase: 16-cleanup-polish-v2
plan: 01
subsystem: ingestion, web-api, web-frontend
tags: [gap-closure, pipeline, sitemap, frontend, deputy-profile]
dependency_graph:
  requires: []
  provides:
    - run_all.py without legacy Step 6 (ingest_deputies.py removed from active pipeline)
    - deputies/index.get.ts with chamber field exposed to frontend
    - sitemap with ~7062 /votes/:id URLs
    - deputy profile voteStats section (Pour/Contre/Abstention/Absent)
    - DeputyCard with AN/Sénat chamber badge
  affects:
    - packages/ingestion/scripts/run_all.py
    - packages/web/server/api/deputies/index.get.ts
    - packages/web/server/api/__sitemap__/urls.ts
    - packages/web/app/pages/deputies/[id].vue
    - packages/web/app/components/DeputyCard.vue
tech_stack:
  added: []
  patterns:
    - v-if guard on voteStats (safe when API returns empty array)
    - Inline mapping object for position label translation (no computed needed for 4 values)
    - v-bind spread on DeputyCard allows new chamber field to pass through automatically from index.vue
key_files:
  created: []
  modified:
    - packages/ingestion/scripts/run_all.py
    - packages/web/server/api/deputies/index.get.ts
    - packages/web/server/api/__sitemap__/urls.ts
    - packages/web/app/pages/deputies/[id].vue
    - packages/web/app/components/DeputyCard.vue
decisions:
  - name: chamber optional prop on DeputyCard
    rationale: Safe if ever null — badge simply won't render; no breaking change to existing usages
  - name: Inline position label mapping (not computed)
    rationale: 4 static values — a computed or utility function adds indirection without benefit
  - name: voteStats placed between tagStats and interventions
    rationale: Logical reading order — topic tags summarize content, vote stats summarize voting behavior, then the detailed interventions
metrics:
  duration: 4 minutes
  completed: 2026-04-05
  tasks_completed: 2
  tasks_total: 2
  commits:
    - hash: c56b7a1
      message: "chore(16-01): backend gap closure — remove legacy Step 6, add chamber to deputies API, add scrutins to sitemap"
    - hash: 2ba0e76
      message: "feat(16-01): frontend gap closure — render voteStats on profile, add chamber badge to DeputyCard"
---

# Phase 16 Plan 01: Milestone 2 Gap Closure Summary

**One-liner:** Removed legacy ingest_deputies.py from pipeline, exposed chamber field in deputies list API, added ~7062 /votes/:id URLs to sitemap, and rendered voteStats with French labels + chamber badges on deputy UI.

## What Was Done

4 independent tech debt items from Milestone 2 audit closed in 2 tasks across 5 files:

### Task 1: Backend Fixes (commit c56b7a1)

**1a. run_all.py — Step 6 removed**
- Removed `--skip-deputies` argparse flag
- Removed Step 6 block running `ingest_deputies.py` (script targeted non-existent `deputies` table)
- Added comment `# Step 6 REMOVED — ingest_deputies.py targeted non-existent 'deputies' table...` in 3 places (docstring, steps list, execution block)
- `ingest_deputies.py` file itself left untouched (dead code reference)

**1b. deputies/index.get.ts — chamber field added**
- Added `chamber: actors.chamber` to the `.select({})` projection
- No other changes needed — `v-bind="deputy"` in `pages/deputies/index.vue` spreads all fields to `DeputyCard` automatically

**1c. __sitemap__/urls.ts — scrutins added**
- Added `scrutins` to the `shared/schema` import
- Added third query in `Promise.all`: `db.select({ id, date }).from(scrutins)`
- Maps to `/votes/${s.id}` URLs with `lastmod` from scrutin date
- ~7062 scrutin URLs now included in sitemap response

### Task 2: Frontend Fixes (commit 2ba0e76)

**2a. deputies/[id].vue — voteStats section**
- Added section between tagStats and interventions list
- Guarded with `v-if="data.voteStats?.length > 0"` — hidden when empty
- Position color coding: green (Pour), red (Contre), gray (Abstention), muted stone (Absent)
- French labels via inline object: `{ for: 'Pour', against: 'Contre', abstain: 'Abstention', absent: 'Absent' }`

**2b. DeputyCard.vue — chamber badge**
- Added optional `chamber?: string | null` prop to `defineProps`
- AN badge: `bg-bronze/10 text-bronze` (matches detail page)
- Sénat badge: `bg-ink/10 text-ink` (matches detail page)
- Wrapped GroupBadge + chamber badges in a flex container for proper layout
- No change needed in `pages/deputies/index.vue` — `v-bind="deputy"` passes through the new `chamber` field automatically

## Deviations from Plan

None — plan executed exactly as written.

## TypeScript Notes

Pre-existing type errors in `server/api/votes/index.get.ts` and `server/api/__sitemap__/urls.ts` related to drizzle-orm dual-version installation (two different `drizzle-orm` versions resolved by pnpm, causing `PgColumn` interface mismatch). These errors existed before this plan and are not introduced by it. No new errors introduced in modified files.

Pre-existing TS2339 errors in `deputies/[id].vue` are from Nuxt's `useFetch` returning `{} | {}` union type for the `data` ref — also pre-existing, not introduced by this plan.

## Self-Check: PASSED

All 5 modified files found. Both task commits verified in git log.
