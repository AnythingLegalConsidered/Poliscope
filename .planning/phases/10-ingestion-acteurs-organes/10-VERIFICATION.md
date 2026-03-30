---
phase: 10-ingestion-acteurs-organes
verified: 2026-03-30T10:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "actor_organs join table created with actor_id FK, organ_id FK, role, start_date, end_date columns"
    - "1311 AN actor-organ memberships ingested from AMO10 ZIP (577 GP + 576 COMPER + 158 DELEG, all with start_date)"
    - "Senat organ dates NULL documented as known data source limitation in ingest_organs_senat.py docstring"
  gaps_remaining: []
  regressions: []
---

# Phase 10: Ingestion Acteurs & Organes - Verification Report

**Phase Goal:** La base contient tous les acteurs parlementaires de la XVIIe legislature (deputes AN + senateurs) et leurs organes d appartenance, avec une table cross-reference qui mappe les IDs entre toutes les sources.
**Verified:** 2026-03-30T10:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 10-03)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | actors table: ~577 AN deputies + ~348 senators, chambre + groupe politique + photo | VERIFIED | DB: 577 AN + 348 Senat (unchanged from 10-01); 0 NULL photo_url; 0 NULL political_group |
| 2 | cross_references maps each actor, zero orphans, UNIQUE constraint active | VERIFIED | DB: 925 cross_references (577 PA + 348 senat); constraint cross_references_actor_source_unique confirmed |
| 3 | Pipelines idempotent — re-run no duplicates | VERIFIED | ON CONFLICT (actor_id, organ_id) DO UPDATE in ingest_memberships_an.py; ON CONFLICT official_id DO UPDATE in actors/organs scripts |
| 4 | Organs in DB with their members and mandate periods | VERIFIED | DB: 1311 actor_organs rows; all 1311 have start_date NOT NULL; distribution: 577 group + 576 commission + 158 delegation; Senat limitation documented |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `packages/shared/drizzle/0004_actor-organs.sql` | CREATE TABLE actor_organs with composite UNIQUE | VERIFIED | 15-line migration with PK, FKs, role, start_date, end_date, UNIQUE(actor_id, organ_id), 2 indexes, GRANT |
| `packages/shared/src/schema.ts` | actorOrgans Drizzle table definition | VERIFIED | Lines 102-113; actorId FK actors, organId FK organs, role, startDate, endDate, 2 indexes |
| `packages/shared/drizzle/meta/_journal.json` | idx=4 entry for 0004_actor-organs | VERIFIED | Entry present at idx=4, tag="0004_actor-organs" |
| `packages/ingestion/scripts/ingest_memberships_an.py` | AN membership ingestion from AMO10 ZIP | VERIFIED | 205 lines; extract_memberships(), resolve_fks(), MEMBERSHIP_UPSERT, _decode() bytes fix; `ingest_memberships_an` function exported |
| `packages/ingestion/scripts/run_all.py` | 8-step pipeline with --skip-memberships | VERIFIED | Step 5 = ingest_memberships_an.py; --skip-memberships in argparse; actor_organs in summary table |
| `packages/ingestion/scripts/ingest_organs_senat.py` | Senat limitation documented | VERIFIED | Lines 6-11: explicit docstring noting no start_date/end_date from senateurs.json and why memberships deferred |

---

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| ingest_actors_an.py | actors table | ON CONFLICT official_id DO UPDATE | WIRED | 577 AN deputies in DB (regression: unchanged) |
| ingest_actors_senat.py | actors table | ON CONFLICT official_id DO UPDATE | WIRED | 348 senators in DB (regression: unchanged) |
| ingest_actors_an.py | cross_references | ON CONFLICT (actor_id, source_type, source_id) DO NOTHING | WIRED | 577 PA rows (regression: unchanged) |
| ingest_actors_senat.py | cross_references | ON CONFLICT (actor_id, source_type, source_id) DO NOTHING | WIRED | 348 senat rows (regression: unchanged) |
| ingest_organs_an.py | organs table | ON CONFLICT official_id DO UPDATE | WIRED | 24 AN organs (regression: unchanged) |
| ingest_organs_senat.py | organs table | ON CONFLICT official_id DO UPDATE | WIRED | 17 Senat organs (regression: unchanged) |
| ingest_memberships_an.py | actor_organs table | ON CONFLICT (actor_id, organ_id) DO UPDATE | WIRED | 1311 rows in DB; constraint actor_organs_actor_organ_unique confirmed in DB |
| ingest_memberships_an.py | actors + organs (FK resolution) | SELECT id, official_id FROM actors/organs WHERE chamber='AN' | WIRED | _decode() helper handles psycopg3 bytes quirk; 0 unresolved actors logged |
| run_all.py | ingest_memberships_an.py | run_script("ingest_memberships_an.py") at Step 5 | WIRED | Conditional on not args.skip_memberships; correct FK order (after organs steps) |

---

### Requirements Coverage

| Requirement | Description | Status | Blocking Issue |
| --- | --- | --- | --- |
| INGEST-01 | Pipeline acteurs AN (deputes XVIIe) | SATISFIED | 577 AN deputies in DB |
| INGEST-02 | Pipeline acteurs Senat (senateurs) | SATISFIED | 348 senators in DB |
| INGEST-03 | Pipeline organes (commissions, groupes politiques) avec membres | SATISFIED | 41 organs + 1311 AN memberships with mandate dates; Senat limitation documented |
| INGEST-09 | Tous les pipelines sont idempotents | SATISFIED | ON CONFLICT patterns in all 5 ingestion scripts verified |

---

### Anti-Patterns Found

None — no TODO/FIXME/placeholder patterns in any of the 6 created/modified files. The Senat membership deferral is explicitly documented as a known data source limitation, not a TODO.

---

### Minor Note (Non-Blocking)

The `actorOrgans` table in `schema.ts` does not declare the composite unique constraint via `uniqueIndex()`. The constraint exists at DB level via migration 0004 (`actor_organs_actor_organ_unique` confirmed in DB), so the ON CONFLICT in the Python script functions correctly. The Drizzle schema is not used for migrations (hand-written SQL, per Phase 9 decision), so this is a schema.ts cosmetic gap only — not a functional issue.

---

### Human Verification Required

None — all automated checks pass. The Senat membership limitation is a documented known gap, not a verification item.

---

## Gaps Summary

No gaps remaining. The single gap from the initial verification (missing actor_organs join table and membership data) has been fully closed:

- actor_organs table exists in schema.ts and live DB with correct columns, FKs, and UNIQUE constraint
- 1311 AN actor-organ memberships ingested with mandate dates (all 1311 have non-NULL start_date)
- Distribution across organ types confirmed: 577 group, 576 commission, 158 delegation
- Senat membership limitation documented in ingest_organs_senat.py — senateurs.json provides no dates, intentionally deferred
- run_all.py updated to 8-step pipeline with --skip-memberships flag

ROADMAP success criterion 4 — "Les organes sont en base avec leurs membres et periodes de mandat" — is satisfied for AN (1311 memberships with mandate periods). Senat memberships without dates are documented as a known data source limitation.

---

_Verified: 2026-03-30T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
