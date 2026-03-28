---
phase: 10-ingestion-acteurs-organes
plan: 01
subsystem: database
tags: [python, postgres, ingestion, actors, cross_references, an, senat, open-data]

# Dependency graph
requires:
  - phase: 09-schema-bdd-universel
    provides: actors, cross_references, legislatures tables with universal schema

provides:
  - 577 AN deputies in actors table (chamber=AN, legislature=17, photo_url, political_group as PO organeRef)
  - 348 senators in actors table (chamber=Senat, actor_type=senator, photo_url, political_group)
  - 577 PA cross_references + 348 senat cross_references
  - UNIQUE constraint on cross_references (actor_id, source_type, source_id) for idempotent upsert
  - ingest_actors_an.py — AN deputies pipeline from open data ZIP
  - ingest_actors_senat.py — Senate actors pipeline from senat.fr API

affects:
  - phase 10-02 (organs ingestion uses actors as FK anchor)
  - phase 11 (debates/interventions reference actors)
  - phase 12 (votes reference actors)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ZIP download with httpx + in-memory zipfile (no disk I/O) for large open data archives"
    - "listify() normalizer for XML-to-JSON fields that can be None/dict/list"
    - "upsert ON CONFLICT official_id + ON CONFLICT (actor_id, source_type, source_id) DO NOTHING for idempotency"
    - "Two-step ingest: actors upsert first, then cross_references via re-query for actor IDs"

key-files:
  created:
    - packages/shared/drizzle/0003_cross-references-unique.sql
    - packages/ingestion/scripts/ingest_actors_an.py
    - packages/ingestion/scripts/ingest_actors_senat.py
  modified:
    - packages/ingestion/scripts/config.py
    - packages/ingestion/scripts/utils.py
    - packages/shared/drizzle/meta/_journal.json

key-decisions:
  - "political_group for AN deputies stores PO organeRef (e.g. PO834720) — resolved to name in Plan 02 when organs are ingested"
  - "legislature=None for senators (Senate has no discrete legislature numbering)"
  - "GRANT ALL on new postgres-owned tables (legislatures, organs, etc.) to poliscope user — tables created by postgres in migration 0002"

patterns-established:
  - "download_zip_json_files() + listify() are shared helpers for AN open data ZIP parsing"
  - "ACTOR_COLUMNS list shared between AN and Senat pipelines — must stay in sync"

# Metrics
duration: 70min
completed: 2026-03-28
---

# Phase 10 Plan 01: Actors Ingestion (AN + Senat) Summary

**577 AN deputies + 348 senators ingested from official sources (open data ZIP + senat.fr API), with PA/senat cross-references and UNIQUE constraint enabling idempotent upsert**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-03-28T17:48:52Z
- **Completed:** 2026-03-28T18:59:30Z
- **Tasks:** 3/3
- **Files modified:** 7

## Accomplishments

- UNIQUE constraint `cross_references_actor_source_unique (actor_id, source_type, source_id)` applied to live DB
- 577 AN deputies upserted with chamber, legislature=17, photo_url, political_group (PO ref), constituency
- 348 senators upserted with chamber=Senat, actor_type=senator, photo_url, political_group, circonscription
- 577 PA + 348 senat cross_references created, both pipelines idempotent
- No NULL photo_url or political_group (AN deputies) — 100% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration 0003 + config/utils updates** - `a5dc027` (chore)
2. **Task 2: AN deputies ingestion pipeline** - `daf7223` (feat)
3. **Task 3: Senat senators ingestion pipeline** - `e2eb915` (feat)

## Files Created/Modified

- `packages/shared/drizzle/0003_cross-references-unique.sql` - UNIQUE constraint on cross_references
- `packages/shared/drizzle/meta/_journal.json` - 0003 entry added
- `packages/ingestion/scripts/config.py` - AN_OPENDATA_ZIP, AN_PHOTO_BASE, SENAT_API_BASE constants
- `packages/ingestion/scripts/utils.py` - download_zip_json_files() and listify() helpers
- `packages/ingestion/scripts/ingest_actors_an.py` - AN deputies pipeline (new)
- `packages/ingestion/scripts/ingest_actors_senat.py` - Senate actors pipeline (new)

## Decisions Made

- **political_group for AN stores PO organeRef** (e.g. "PO834720"): GP mandate organeRef is a reference to an organ, not a name. Will be resolved to human-readable name when organs are ingested in Plan 02.
- **legislature=None for senators**: Senate has no discrete legislature numbering, unlike AN.
- **GRANT ALL on postgres-owned tables**: Tables created by postgres user in migration 0002 (legislatures, organs, scrutins, votes, questions, amendments, cross_references) — poliscope user needed explicit GRANT to insert.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Unwrap {"acteur": {...}} JSON wrapper from ZIP files**
- **Found during:** Task 2 (AN deputies ingestion pipeline)
- **Issue:** Each PA*.json file in the ZIP wraps the actor under an "acteur" key — raw dict had no "uid" at top level
- **Fix:** Added `v["acteur"]` unwrap before calling `map_an_actor()`
- **Files modified:** packages/ingestion/scripts/ingest_actors_an.py
- **Verification:** 577 actors mapped without KeyError
- **Committed in:** daf7223 (Task 2 commit)

**2. [Rule 1 - Bug] Handle uid as XML-typed object {"#text": "PA841657"}**
- **Found during:** Task 2 (AN deputies ingestion pipeline)
- **Issue:** The uid field in AN actor JSON is not a plain string — it's an XML-to-JSON object `{"@xmlns:xsi": ..., "#text": "PA841657"}`. `str.removeprefix()` called on dict caused AttributeError.
- **Fix:** Added isinstance check: `uid = uid_raw["#text"] if isinstance(uid_raw, dict) else uid_raw`
- **Files modified:** packages/ingestion/scripts/ingest_actors_an.py
- **Verification:** uid extracted correctly, photo_url numeric ID stripped without error
- **Committed in:** daf7223 (Task 2 commit)

**3. [Rule 2 - Missing Critical] Grant permissions on postgres-owned tables to poliscope user**
- **Found during:** Task 2 (first DB write attempt)
- **Issue:** Tables created by postgres user in migration 0002 had no poliscope user permissions — INSERT into legislatures raised InsufficientPrivilege
- **Fix:** `GRANT ALL ON TABLE legislatures, organs, scrutins, votes, questions, amendments, cross_references TO poliscope` + `GRANT USAGE, SELECT ON ALL SEQUENCES`
- **Files modified:** none (live DB grant via SSH)
- **Verification:** Subsequent inserts succeeded without permission errors
- **Committed in:** N/A (DB-level fix, no file change needed)

**4. [Rule 1 - Bug] senat.fr API returns plain list, not wrapped dict**
- **Found during:** Task 3 (Senat senators ingestion pipeline)
- **Issue:** Plan described API as returning `{"senateurs": [...]}` but actual response is a plain JSON list. fetch_json() utility type-hints return as dict.
- **Fix:** Wrote `fetch_senators()` directly using httpx instead of `fetch_json()`, with fallback: `data if isinstance(data, list) else data.get("senateurs", [])`
- **Files modified:** packages/ingestion/scripts/ingest_actors_senat.py
- **Verification:** 348 senators fetched correctly
- **Committed in:** e2eb915 (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 bugs in AN data format, 1 Rule 2 missing permissions, 1 Rule 1 API shape mismatch)
**Impact on plan:** All auto-fixes required for correctness. No scope creep. The AN XML-to-JSON artifacts and postgres ownership gaps are predictable in this stack.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- actors table: 577 AN + 348 Senat = 925 actors, complete FK root for phases 11-12
- cross_references: 925 entries (577 PA + 348 senat) with UNIQUE constraint
- political_group for AN deputies stores PO organeRef — Plan 02 organs ingestion will need to resolve these to names
- GRANT permissions on postgres-owned tables confirmed working

---
*Phase: 10-ingestion-acteurs-organes*
*Completed: 2026-03-28*
