---
phase: 12-ingestion-votes-scrutins
plan: 02
subsystem: database
tags: [python, psycopg3, httpx, zipfile, sql-parsing, votes, scrutins, dosleg, senat]

requires:
  - phase: 10-ingestion-acteurs-organes
    provides: actors table with chamber='Senat' entries and official_id = senator matricule

provides:
  - ingest_scrutins_senat.py: Senat scrutins + votes pipeline (Dosleg SQL dump text parsing)
  - 1154 scrutins in scrutins table (chamber='Senat', XVIIe legislature 2022-2026)
  - 361853 votes in votes table with senator linkage via actors.official_id
  - SENAT_DOSLEG_ZIP constant in config.py
  - run_all.py: 11-step pipeline (Step 10 = Senat scrutins)

affects: [12-03-ingestion-votes, 13-api-votes, 14-ui-votes]

tech-stack:
  added: []
  patterns:
    - "Dosleg plain-SQL dump text parsing: extract COPY blocks by table name, tab-split rows"
    - "actors.official_id direct lookup for Senat (senmat == official_id, no cross_references needed)"
    - "DELETE + INSERT per scrutin_id for idempotent vote ingestion (Senat)"
    - "scr result: adopted if scrpou > scrcon, rejected otherwise (no explicit result column)"
    - "SENAT_{sesann}_{scrnum} format for official_id (prevents AN collision)"

key-files:
  created:
    - packages/ingestion/scripts/ingest_scrutins_senat.py
  modified:
    - packages/ingestion/scripts/config.py
    - packages/ingestion/scripts/run_all.py

key-decisions:
  - "Text-parse Dosleg SQL dump instead of PG restore — simpler, no throwaway DB setup, identical result"
  - "result computed from scrpou > scrcon — no explicit result column in Dosleg scr table"
  - "official_id = SENAT_{sesann}_{scrnum} — sesann is the session start year (2022=session 2022-2023)"
  - "senator matching direct via actors.official_id (no cross_references) — senmat and official_id format match exactly"
  - "delegation_actor_id = None for v1 — senmatdel tracked but deferred"
  - "votes_abstain computed from scrvot - scrpou - scrcon — not stored in scr table directly"

duration: ~50min (2x pipeline runs: initial + idempotency check, ~25 min each)
completed: 2026-03-31
---

# Phase 12 Plan 02: Senat Scrutins/Votes Ingestion Summary

**Senat public vote pipeline ingesting 1154 scrutins and 361,853 individual senator vote positions from the Dosleg PostgreSQL dump at data.senat.fr, using direct actors.official_id matching (90.2% match rate)**

## Performance

- **Duration:** ~50min (2 pipeline runs: first execution + idempotency verification)
- **Started:** 2026-03-31T11:12:12Z
- **Completed:** 2026-03-31T14:19:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- 1,154 Senat scrutins ingested from Dosleg dump (XVIIe legislature, 2022-06-22 onward)
- 361,853 individual senator vote positions (for=170186, against=160639, abstain=20071, absent=10957)
- 90.2% senator match rate (361853/401396 total vote rows resolved via actors.official_id)
- 39,543 unmatched senmat = senators who voted in 2022+ but are not current senators in DB (retired, replaced, etc.)
- Dosleg schema discovered: plain SQL dump, scr + votsen tables, posvot codes 1-4
- Pipeline is idempotent — re-run produces identical counts (verified second run)
- run_all.py updated to 11-step pipeline (Step 10 = Senat scrutins)
- Both chambers now complete: 5908 AN + 1154 Senat = 7062 total scrutins in DB

## Task Commits

1. **Task 1: Schema discovery + create ingest_scrutins_senat.py** - `c0467d1` (feat)
2. **Task 2: Execute pipeline + update run_all.py** - `fe6e76c` (feat)

**Plan metadata:** (docs commit follows)

## Schema Discovery Findings

The Dosleg PostgreSQL 8.4 dump is a plain-text SQL file (122 MB uncompressed). No pg_restore needed — direct text parsing of COPY blocks is simpler and sufficient.

**Key tables:**
- `scr(sesann, scrnum, code, scrint, scrdat, scrpou, scrcon, scrvot, scrsuf, ...)` — scrutin records
  - `sesann`: session start year (2022 = session 2022-2023), used as part of official_id
  - `scrint`: scrutin title (up to 4000 chars)
  - `scrdat`: timestamp `YYYY-MM-DD HH:MM:SS` — parsed to date
  - `scrpou`/`scrcon`: votes for/against — result computed as `scrpou > scrcon`
- `votsen(sesann, scrnum, senmat, posvotcod, ...)` — individual senator votes
  - `senmat`: senator matricule, `character(6)` — stripped to match `actors.official_id` format
  - `posvotcod`: 1=pour, 2=contre, 3=abstention, 4=non-votant
- `posvot`: reference table for vote positions (codes 1-4)
- `stavot`: special voter statuses (0=none, 8=session chair, 9=government member, etc.)

**Data scope:**
- Total scr rows: 4,642 (all years since 2006)
- XVIIe filter (scrdat >= 2022-06-22): 1,154 scrutins (3,488 older skipped)
- Total votsen rows: 1,614,888 (all years)
- XVIIe votsen rows: 401,396 (361,853 matched = 90.2%)

**PG 17 compatibility:** Not tested — plain text parsing made this irrelevant.

## Files Created/Modified

- `packages/ingestion/scripts/ingest_scrutins_senat.py` — Senat scrutins/votes pipeline
  - `_download_dosleg_sql()`: streaming download + ZIP extraction to UTF-8 string
  - `_parse_copy_block()`: extract COPY block rows from plain SQL by table name
  - `parse_scrutins()`: filter + map scr rows to scrutins schema (XVIIe filter, result computation)
  - `parse_votes()`: map votsen rows to votes schema (grouped by scrutin key)
  - `load_actor_cache_senat()`: `{official_id: actor_id}` for all Senat actors
  - `ingest_scrutins_senat()`: main pipeline with upsert/delete+insert idempotency
- `packages/ingestion/scripts/config.py` — Added `SENAT_DOSLEG_ZIP` constant
- `packages/ingestion/scripts/run_all.py` — Added Step 10 (ingest_scrutins_senat.py), updated docstring

## Decisions Made

- **Text parsing instead of PG restore**: Dosleg dump is plain SQL — extracting COPY blocks via Python string matching is simpler than setting up a throwaway PG database. Equivalent result, less infrastructure.
- **Direct `actors.official_id` match**: Senator matricule (`senmat`) matches `actors.official_id` exactly (after `.strip()` for character(6) padding). No `cross_references` table needed unlike AN deputies.
- **`official_id = SENAT_{sesann}_{scrnum}`**: Compound key using session year + scrutin number avoids collisions with AN UIDs (e.g., `VTANR5L17V4785`). Scrutin numbers reset each session so both components are required.
- **Result from `scrpou > scrcon`**: The `scr` table has no explicit result/adoption column. Computed result from vote counts is equivalent and confirmed correct by inspecting sample rows.
- **`votes_abstain = scrvot - scrpou - scrcon`**: Abstentions not stored directly in scr; computed from total voters minus for+against. `max(0, ...)` guard handles any floating-point edge cases.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as designed. The Dosleg schema was unknown before Task 1 but the text-parsing approach worked first try. No PG compatibility issues encountered because plain text parsing bypassed the PG restore entirely.

---

**Total deviations:** 0 — plan executed exactly as written.

## Issues Encountered

- Pipeline ran twice (initial execution + idempotency check). Each run took ~25 minutes for 1154 scrutins due to per-vote INSERT pattern (same approach as AN pipeline). This is expected and acceptable for a daily/weekly ingestion script.
- The 39,543 unmatched senmat values (9.8%) are expected: senators who served in 2022+ but are no longer active (retired, replaced at by-elections, etc.) are not in the actors table which was ingested from the current senators list.
- `soslib` field (notes in base of page) is `\N` for all recent scrutins — this is normal (the column is vestigial in recent data).

## User Setup Required

None — pipeline uses existing DATABASE_URL and runs on the production LXC.

## Next Phase Readiness

- scrutins and votes tables fully populated for both chambers (Phase 13 API endpoints ready)
- AN: 5,908 scrutins, 946,659 votes | Senat: 1,154 scrutins, 361,853 votes
- Total: 7,062 scrutins, 1,308,512 votes in DB
- `--skip-scrutins` flag covers both AN and Senat in run_all.py
- Phase 12-03 (if any) or Phase 13 API can now expose bicameral vote data

---
*Phase: 12-ingestion-votes-scrutins*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FOUND: ingest_scrutins_senat.py
- FOUND: config.py (SENAT_DOSLEG_ZIP)
- FOUND: run_all.py (ingest_scrutins_senat)
- FOUND: 12-02-SUMMARY.md
- FOUND: commit c0467d1 (Task 1)
- FOUND: commit fe6e76c (Task 2)
