---
phase: 10-ingestion-acteurs-organes
plan: 02
subsystem: database
tags: [python, postgres, ingestion, organs, an, senat, open-data, political-groups]

# Dependency graph
requires:
  - phase: 10-01
    provides: 577 AN deputies + 348 senators in actors table with PO organeRef in political_group

provides:
  - 24 AN organs (12 groups, 8 commissions permanentes, 4 delegations) in organs table
  - 17 Senat organs (9 political groups, 8 commissions permanentes) in organs table
  - AN actors.political_group resolved from PO organeRef to human-readable short name (577 actors)
  - ingest_organs_an.py — AN organs pipeline from AMO10 ZIP
  - ingest_organs_senat.py — Senat organs pipeline from senateurs.json API
  - run_all.py — updated orchestrator with correct table names and 7-step pipeline

affects:
  - future actor-organ membership queries (organs as FK anchor)
  - political group display in UI (short_name available: RN, EPR, LFI-NFP, etc.)
  - phase 11 (debates reference actors whose political_group is now human-readable)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ORGAN_TYPE_FILTER set-based filter: only ingest GP/COMPER/DELEG for AN, COMMISSION/DELEGATION for Senat"
    - "SENAT_ prefix on official_id prevents collision between Senat and AN organ IDs"
    - "Slug-based stable official_id for Senat political groups: SENAT_GP_{slugified_libelle}"
    - "Two-phase pipeline: actors upsert first (stores PO refs), then organs upsert + UPDATE actors resolves refs"
    - "has_updated_at=False on organs upsert: organs table has created_at only"

key-files:
  created:
    - packages/ingestion/scripts/ingest_organs_an.py
    - packages/ingestion/scripts/ingest_organs_senat.py
  modified:
    - packages/ingestion/scripts/run_all.py

key-decisions:
  - "Filter AN organs to GP/COMPER/DELEG: skip ASSEMBLEE/BUREAU/OFFPAR (meta-organs not useful for actor-organ queries)"
  - "Filter Senat organs to COMMISSION/DELEGATION: skip ETUDE/GIA/OFFICE (out of Phase 10 scope)"
  - "SENAT_ prefix + slug-based IDs for Senat organs: ensures stable, collision-free official_id"
  - "political_group resolution via SQL UPDATE actors SET political_group = o.short_name FROM organs o: resolves 577 PO refs in one query"
  - "run_all.py pipeline plan log: shows RUN/SKIP for each step at startup for visibility"

patterns-established:
  - "Organ ingestion: map() returns None for filtered types, list comprehension skips None"
  - "Political group resolution: separate UPDATE after organs upsert (not inline)"

# Metrics
duration: ~5min
completed: 2026-03-28
---

# Phase 10 Plan 02: Organs Ingestion (AN + Senat) Summary

**41 organs ingested from official sources (AMO10 ZIP + senat.fr API): 24 AN organs (12 groups, 8 commissions, 4 delegations) + 17 Senat organs (9 groups, 8 commissions); 577 AN actors' political_group resolved from PO organeRef to human-readable short names**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-28T18:04:05Z
- **Completed:** 2026-03-28T18:09:00Z
- **Tasks:** 3/3
- **Files modified:** 3

## Accomplishments

- 24 AN organs upserted (12 groups: RN/EPR/LFI-NFP/SOC/DR/EcoS/Dem/HOR/LIOT/GDR/etc., 8 commissions permanentes, 4 delegations)
- 17 Senat organs upserted (9 political groups, 8 commissions permanentes) with SENAT_ prefixed official_ids
- 577 AN actors' political_group resolved from PO organeRef (e.g. "PO834720") to human-readable short name (e.g. "RN", "EPR")
- run_all.py updated: correct table names in summary, 7-step pipeline, --skip-actors/--skip-organs flags
- Full pipeline idempotent: double run produces identical DB state (actors=1543, organs=41, cross_refs=925)

## Task Commits

Each task was committed atomically:

1. **Task 1: AN organs ingestion pipeline** - `c35c776` (feat)
2. **Task 2: Senat organs ingestion pipeline** - `343d921` (feat)
3. **Task 3: Update run_all.py orchestrator** - `96de827` (feat)

## Files Created/Modified

- `packages/ingestion/scripts/ingest_organs_an.py` - AN organs pipeline (new)
- `packages/ingestion/scripts/ingest_organs_senat.py` - Senat organs pipeline (new)
- `packages/ingestion/scripts/run_all.py` - 7-step orchestrator with correct table names and skip flags (modified)

## Decisions Made

- **Filter AN organs to GP/COMPER/DELEG**: ASSEMBLEE/BUREAU/OFFPAR are meta-organs that don't appear in actor-organ memberships — keeping organs table focused.
- **SENAT_ prefix for Senat official_ids**: Senat organ codes like "COM-LOIS" could collide with future sources — prefix makes them unambiguous.
- **Slug-based IDs for Senat groups**: `SENAT_GP_{slugified_libelle}` is stable across runs (libelle doesn't change), collision-free.
- **political_group resolution via single SQL UPDATE**: Simpler and more efficient than in-Python lookup — one UPDATE resolves all 577 actors at once.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — no data format surprises (AN organ files follow same `{"organe": {...}}` wrapper pattern as actor files).

## Verification Results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| AN organs by type | groups ~10-15, commissions ~8-10, delegations ~5-10 | 12 groups, 8 commissions, 4 delegations | PASS |
| Senat organs by type | commissions ~7-8, groups ~8-10 | 8 commissions, 9 groups | PASS |
| AN actors with PO% political_group | 0 | 0 | PASS |
| NULL photo_url (AN + Senat) | 0 or near-0 | 0 | PASS |
| run_all.py --help shows --skip-actors, --skip-organs | yes | yes | PASS |
| print_summary() references organs, actors (not deputies) | yes | yes | PASS |
| Double pipeline run = identical counts | yes | yes | PASS |

## Next Phase Readiness

- organs table: 41 rows (24 AN + 17 Senat), ready as FK anchor for actor-organ memberships
- AN actors: political_group is human-readable (RN, EPR, LFI-NFP, etc.) — ready for UI display
- Phase 10 complete — actors and organs fully seeded
- Phase 11 (debates/interventions ingestion): actors table ready with correct official_id format

---
*Phase: 10-ingestion-acteurs-organes*
*Completed: 2026-03-28*

## Self-Check: PASSED

- FOUND: packages/ingestion/scripts/ingest_organs_an.py
- FOUND: packages/ingestion/scripts/ingest_organs_senat.py
- FOUND: .planning/phases/10-ingestion-acteurs-organes/10-02-SUMMARY.md
- FOUND commit c35c776: feat(10-02): AN organs ingestion pipeline + political_group resolution
- FOUND commit 343d921: feat(10-02): Senat organs ingestion pipeline
- FOUND commit 96de827: feat(10-02): update run_all.py orchestrator for 7-step pipeline
