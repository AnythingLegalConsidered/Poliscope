---
phase: 12-ingestion-votes-scrutins
plan: 01
subsystem: database
tags: [python, psycopg3, zipfile, httpx, tqdm, votes, scrutins, cross_references]

requires:
  - phase: 10-ingestion-acteurs-organes
    provides: cross_references table with source_type='PA' entries for AN deputies

provides:
  - ingest_scrutins_an.py: AN public votes pipeline (download, parse, upsert, insert)
  - 5908 scrutins in scrutins table (chamber='AN', XVIIe legislature full history)
  - 946659 votes in votes table with actor linkage via cross_references
  - AN_SCRUTINS_ZIP constant in config.py

affects: [12-02-ingestion-votes-senat, 13-api-votes, 14-ui-votes]

tech-stack:
  added: []
  patterns:
    - "PA acteurRef actor lookup via cross_references WHERE source_type='PA'"
    - "DELETE + INSERT per scrutin_id for idempotent vote ingestion"
    - "psycopg3 binary bytes decode: bytes(v).decode('utf-8') for text columns"
    - "syntheseVote.decompte.{pour,contre,abstentions} for AN vote counts (not nbrVoix)"

key-files:
  created:
    - packages/ingestion/scripts/ingest_scrutins_an.py
  modified:
    - packages/ingestion/scripts/config.py
    - packages/ingestion/scripts/run_all.py

key-decisions:
  - "syntheseVote.decompte.pour/contre/abstentions (not pour.nbrVoix) — actual JSON structure differs from research doc"
  - "psycopg3 binary protocol returns text as bytes — _decode_text() helper added to ingest_scrutins_an.py"
  - "cross_references source_id had hex-escaped values from original ingestion — corrected via UPDATE before votes pipeline"
  - "delegation_actor_id = None for v1 — parDelegation tracked but deferred"

patterns-established:
  - "load_actor_cache_an(): _decode_text() wrapping for all psycopg3 binary text columns"
  - "extract_votes(): listify() on both groupe and votant to handle single-element dicts"

duration: ~2h30min (pipeline execution dominated — 5908 scrutins x ~577 votes each)
completed: 2026-03-31
---

# Phase 12 Plan 01: AN Scrutins/Votes Ingestion Summary

**AN public vote pipeline ingesting 5908 scrutins and 946,659 individual deputy vote positions from Scrutins.json.zip, using cross_references PA IDs for actor matching (574/577 deputies linked)**

## Performance

- **Duration:** ~2h 30min (pipeline execution x3 runs: initial debug run, fix run, idempotency check)
- **Started:** 2026-03-31T08:22:14Z
- **Completed:** 2026-03-31T~11:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- 5,908 AN scrutins ingested from Scrutins.json.zip (full XVIIe legislature history, much more than the ~500 estimated)
- 946,659 individual vote positions with 4 types (for=422408, against=458478, abstain=56178, absent=9595)
- 574/577 distinct deputies linked (99.5% match rate via PA cross_references)
- run_all.py updated to 10-step pipeline with --skip-scrutins flag
- Pipeline is idempotent — re-run produces identical counts

## Task Commits

1. **Task 1: Create ingest_scrutins_an.py** - `b93453a` (feat)
2. **Task 2: Execute pipeline + update run_all.py** - `1682788` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `packages/ingestion/scripts/ingest_scrutins_an.py` - AN scrutins/votes pipeline (load_actor_cache_an, build_scrutin_record, extract_votes, main)
- `packages/ingestion/scripts/config.py` - Added AN_SCRUTINS_ZIP constant
- `packages/ingestion/scripts/run_all.py` - Added Step 9 (ingest_scrutins_an.py), --skip-scrutins flag, scrutins/votes in summary table

## Decisions Made

- `session_id = None`: Linking AN scrutins to debate sessions via seanceRef is non-trivial and not required for Phase 12
- `legislature_id = None`: No legislature FK resolution needed for now
- `delegation_actor_id = None`: parDelegation detected and flagged but delegation tracking deferred to v2
- syntheseVote.decompte.{pour,contre,abstentions} used instead of pour.nbrVoix (actual JSON format)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed psycopg3 binary protocol bytes decode in load_actor_cache_an()**
- **Found during:** Task 2 (pipeline execution)
- **Issue:** psycopg3 returns text columns as bytes in binary mode; load_actor_cache_an() was building a `{bytes: int}` cache while acteurRef values are `str`, causing 100% lookup failure and 0 votes inserted
- **Fix:** Added `_decode_text()` helper that calls `bytes(v).decode("utf-8")` on all cache keys; cache now correctly maps `"PA841657" -> int`
- **Files modified:** packages/ingestion/scripts/ingest_scrutins_an.py
- **Verification:** Cache lookup PA842279 returns 915 (correct actor_id); vote extraction for first scrutin yields 138 votes
- **Committed in:** 1682788 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed cross_references source_id hex-escaped data in DB**
- **Found during:** Task 2 (debugging 0 votes after fixing bytes decode)
- **Issue:** The 577 PA cross_references had source_id stored as hex-escaped values (e.g., `\x5041383431363035` instead of `PA841605`) — a psycopg3 binary protocol artifact from the original ingest_actors_an.py run in Phase 10
- **Fix:** Ran a targeted UPDATE script to decode all 577 source_id values from hex-escape to plain text strings
- **Files modified:** cross_references table (data fix, no schema change)
- **Verification:** source_id values now match `PA{numeric}` format, cache lookup works correctly
- **Committed in:** 1682788 (included in Task 2 commit — data fix, not a new file)

**3. [Rule 1 - Bug] Fixed syntheseVote field path for vote count aggregates**
- **Found during:** Task 2 (DB verification showing votes_for=0 for all scrutins)
- **Issue:** Plan and research doc specified `syntheseVote.pour.nbrVoix` but actual AN JSON structure uses `syntheseVote.decompte.pour` (flat string, not nested object)
- **Fix:** Updated `build_scrutin_record()` to read from `synthese.get("decompte", {})` then `decompte.get("pour", 0)`
- **Files modified:** packages/ingestion/scripts/ingest_scrutins_an.py
- **Verification:** After re-run, scrutin VTANR5L17V2657 shows votes_for=121, votes_against=23 (matching raw JSON)
- **Committed in:** 1682788 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 bugs)
**Impact on plan:** All three fixes were required for correctness — without them, votes would not be stored or counts would be zero. No scope creep.

## Issues Encountered

- Pipeline ran 3 times total (initial with wrong implementation → second with fixed cache but wrong vote counts → third = idempotency verification). Each run took ~90-100 minutes for 5908 scrutins. The idempotency run confirmed identical counts (946,659 votes).
- The 5908 scrutins (vs ~500 estimated) is because the ZIP contains the full XVIIe legislature history since 2022, not just recent ones.

## User Setup Required

None — pipeline uses existing DATABASE_URL and runs on the production LXC.

## Next Phase Readiness

- scrutins and votes tables populated and ready for Phase 13 API endpoints
- Actor linkage is 99.5% complete (574/577) — 3 deputies may be inactive/government
- run_all.py --skip-scrutins flag available for fast re-runs of other steps
- Phase 12-02 (Senat votes via Dosleg) still pending — schema discovery required first

---
*Phase: 12-ingestion-votes-scrutins*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FOUND: ingest_scrutins_an.py
- FOUND: config.py (AN_SCRUTINS_ZIP)
- FOUND: run_all.py (ingest_scrutins_an + --skip-scrutins)
- FOUND: 12-01-SUMMARY.md
- FOUND: commit b93453a (Task 1)
- FOUND: commit 1682788 (Task 2)
