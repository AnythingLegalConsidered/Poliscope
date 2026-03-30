---
phase: 11-ingestion-debats-cri
plan: 01
subsystem: ingestion
tags: [python, postgres, actors, debates, interventions, cri, xml, an]

requires:
  - phase: 10-ingestion-acteurs-organes
    provides: actors table with chamber='AN' filter and official_id PA-prefixed IDs

provides:
  - ingest_debates.py fully refactored to use actors table with chamber column
  - PA prefix fix ensuring AN actor matching works via official_id

affects:
  - 11-02 (Senat CRI pipeline — normalize_name() reused)
  - 11-03 (run_all.py orchestrator — stats keys changed)

tech-stack:
  added: []
  patterns:
    - "Actor matching: prepend 'PA' prefix to DILA href fiche ID before actors.official_id lookup"
    - "chamber column on both debates and interventions for multi-chamber queries"

key-files:
  created: []
  modified:
    - packages/ingestion/scripts/ingest_debates.py

key-decisions:
  - "PA prefix prepend in match_actor(): DILA hrefs give raw numeric IDs (795746), actors.official_id stores PA-prefixed IDs (PA795746)"
  - "chamber='AN' hardcoded in both build_debate_record() and build_intervention_records() — not derived from XML metadata"

patterns-established:
  - "load_actor_cache() pattern: SELECT id, official_id, full_name FROM actors WHERE chamber = 'AN'"
  - "Stats keys actor_matches/actor_unmatched (not deputy_*)"

duration: 10min
completed: 2026-03-30
---

# Phase 11 Plan 01: AN CRI Pipeline — actors table migration Summary

**ingest_debates.py refactored from deputies table to actors table with chamber='AN' filter, PA-prefix actor matching, and chamber column on both debates and interventions**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-30T~session
- **Completed:** 2026-03-30
- **Tasks:** 1/1
- **Files modified:** 1

## Accomplishments

- Renamed `load_deputy_cache()` to `load_actor_cache()` — query now `FROM actors WHERE chamber = 'AN'`
- Fixed actor ID matching: DILA hrefs give `795746`, actors store `PA795746` — prepend `PA` before lookup
- Added `chamber='AN'` to both `DEBATE_COLUMNS` and `INTERVENTION_COLUMNS`
- Renamed `deputy_id` to `actor_id` throughout (column key, function variable, stats)
- Zero stale references to `deputies` table or `deputy_id` remain in the file

## Task Commits

1. **Task 1: Refactor ingest_debates.py — deputy to actor migration** - `26ca3ba` (refactor)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified

- `packages/ingestion/scripts/ingest_debates.py` — Full refactor: actors table, PA prefix, chamber columns, renamed identifiers

## Decisions Made

- PA prefix is prepended at match time (not stored separately) — consistent with how actors.official_id was ingested in phase 10
- `chamber` hardcoded as `"AN"` string literal, not derived from XML — avoids ambiguity in multi-chamber queries

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `ingest_debates.py` is ready for a live dry-run against the DILA endpoint
- `normalize_name()` is untouched and available for reuse by the Senat pipeline (plan 11-02)
- Stats keys changed (`actor_matches`/`actor_unmatched`) — run_all.py will need updating when it references these keys (plan 11-03 or equivalent)

---
*Phase: 11-ingestion-debats-cri*
*Completed: 2026-03-30*
