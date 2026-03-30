---
phase: 10-ingestion-acteurs-organes
plan: 03
subsystem: database
tags: [postgres, python, drizzle, psycopg3, ingestion, actor-organs]

# Dependency graph
requires:
  - phase: 10-01
    provides: 577 AN actors + 348 Senat actors in actors table
  - phase: 10-02
    provides: 24 AN organs + 17 Senat organs in organs table

provides:
  - actor_organs join table (schema.ts + migration 0004 + live DB)
  - 1311 AN actor-organ memberships with role, start_date, end_date
  - ingest_memberships_an.py — idempotent upsert via ON CONFLICT(actor_id, organ_id)
  - run_all.py 8-step pipeline with --skip-memberships flag
  - Senat organ dates limitation documented in ingest_organs_senat.py

affects: [phase-11, phase-12, phase-13, api-endpoints]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "actor_organs composite unique constraint enables idempotent upsert without helper"
    - "psycopg3 binary protocol returns text as bytes — decode with _decode() helper on FK lookup"
    - "Hand-written SQL migration (0004) + manual _journal.json update — consistent with Phase 9 decision"

key-files:
  created:
    - packages/shared/drizzle/0004_actor-organs.sql
    - packages/ingestion/scripts/ingest_memberships_an.py
  modified:
    - packages/shared/src/schema.ts
    - packages/shared/drizzle/meta/_journal.json
    - packages/ingestion/scripts/run_all.py
    - packages/ingestion/scripts/ingest_organs_senat.py

key-decisions:
  - "actor_organs unique on (actor_id, organ_id) — deduplicates multiple mandats per actor+organ pair, keeps most recent"
  - "psycopg3 binary protocol quirk: text columns return as bytes — decode on FK lookup, not a connection setting change"
  - "Senat memberships not ingested — senateurs.json lacks membership dates, incomplete data worse than no data"

patterns-established:
  - "Pattern: multi-column conflict upsert — write raw SQL, not upsert_query() helper (single-column only)"
  - "Pattern: FK resolution via SELECT id, official_id — decode bytes if psycopg3 binary mode active"

# Metrics
duration: 15min
completed: 2026-03-30
---

# Phase 10 Plan 03: Actor-Organs Gap Closure Summary

**actor_organs join table with 1311 AN memberships (GP/COMPER/DELEG mandats with dates and roles), idempotent pipeline, Senat limitation documented**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-30T09:28:00Z
- **Completed:** 2026-03-30T09:43:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created actor_organs table (Drizzle schema + SQL migration 0004) with composite UNIQUE(actor_id, organ_id), FKs with CASCADE, and indexes — applied to live DB
- Ingested 1311 AN actor-organ memberships from AMO10 ZIP mandats (577 GP + 576 COMPER + 158 DELEG, 1422 source rows deduplicated to 1311 by unique constraint)
- Updated run_all.py to 8-step pipeline with --skip-memberships flag and actor_organs in summary table
- Documented Senat organ dates and membership limitation in ingest_organs_senat.py docstring

## Task Commits

Each task was committed atomically:

1. **Task 1: Create actor_organs table (schema + migration 0004)** - `f7b0a0b` (feat)
2. **Task 2: Ingest AN memberships + update orchestrator + document Senat gap** - `6c69ad6` (feat)

## Files Created/Modified

- `packages/shared/src/schema.ts` — Added actorOrgans table definition with FKs, indexes
- `packages/shared/drizzle/0004_actor-organs.sql` — Hand-written migration with UNIQUE(actor_id, organ_id) constraint
- `packages/shared/drizzle/meta/_journal.json` — Added idx=4 entry for 0004_actor-organs
- `packages/ingestion/scripts/ingest_memberships_an.py` — AN membership ingestion: extract mandats, resolve FKs, batch upsert
- `packages/ingestion/scripts/run_all.py` — 8-step pipeline, --skip-memberships, actor_organs in summary
- `packages/ingestion/scripts/ingest_organs_senat.py` — Senat limitation documented in docstring

## Decisions Made

- **actor_organs unique on (actor_id, organ_id):** Some actors have multiple mandats for the same organ (left and rejoined). The UNIQUE constraint deduplicates to 1311 rows from 1422 source rows — always keeps the most recent values via ON CONFLICT DO UPDATE.
- **psycopg3 binary protocol:** psycopg3 v3.3.2 returns `text` columns as `bytes` in binary protocol. Fixed with a `_decode()` helper on FK lookup maps. No connection-level setting change (would affect all other scripts).
- **Senat memberships deferred:** senateurs.json `organismes[]` provides code/type/libelle but no dates. Ingesting memberships without dates would fail the ROADMAP criterion "periodes de mandat." Documented as known limitation, not a blocker for Phase 10 completion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] psycopg3 binary protocol returns text as bytes**
- **Found during:** Task 2 (FK resolution in ingest_memberships_an.py)
- **Issue:** `actor_id_map` built from `SELECT id, official_id FROM actors` had bytes keys (b'PA330008') while memberships used string keys ('PA330008') — zero FK matches, 0 rows upserted
- **Fix:** Added `_decode()` helper to normalize bytes/memoryview to str when building lookup maps
- **Files modified:** packages/ingestion/scripts/ingest_memberships_an.py
- **Verification:** Re-ran ingest — 1422 resolved (0 skipped), 1311 rows in DB, idempotent on second run
- **Committed in:** 6c69ad6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential for correctness — without fix, 0 rows would have been inserted. No scope creep.

## Issues Encountered

- SSH psql peer auth failure: `ssh poliscope-db "psql -U poliscope"` uses peer auth, needs `-h 192.168.2.200` for TCP + PGPASSWORD for scram-sha-256. Same pattern as previous migrations — used `ssh poliscope-db "PGPASSWORD=... psql -h 192.168.2.200 ..."`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ROADMAP criterion 4 satisfied: AN organs have members with mandate dates (1311 rows)
- Senat membership limitation documented — not a blocker for Phase 11+
- actor_organs table ready for API exposure in Phase 13
- Phase 11 (XML debates/interventions) can proceed — no dependency on actor_organs

---
*Phase: 10-ingestion-acteurs-organes*
*Completed: 2026-03-30*
