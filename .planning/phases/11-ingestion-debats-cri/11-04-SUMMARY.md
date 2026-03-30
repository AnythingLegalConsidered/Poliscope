---
phase: 11-ingestion-debats-cri
plan: 04
subsystem: ingestion
tags: [senat, cri, pipeline, ingestion, tagging]
dependency_graph:
  requires: [11-02, 11-03]
  provides: [senat-debates-in-db, senat-interventions-tagged]
  affects: [debates-api, search, debates-ui]
tech_stack:
  added: []
  patterns:
    - lxml XMLParser(recover=True) for malformed HTML/XML Senat CRI files
    - mat attribute (senator matricule) as primary actor matching strategy
    - filename-based date extraction for Senat CRI
key_files:
  created: []
  modified:
    - packages/ingestion/scripts/ingest_debates_senat.py
decisions:
  - decision: "Filename regex dYYYYMMDD.xml instead of SEN_YYYYMMDD_NNN.xml"
    rationale: "Actual cri.zip format uses cri/dYYYYMMDD.xml — prior regex matched 0 files"
  - decision: "lxml XMLParser(recover=True) for Senat CRI XML"
    rationale: "394 of 413 XVIIe files fail strict XML parse (tag mismatches in HTML/XML mix); recover=True parses all 413 correctly"
  - decision: "mat attribute as primary senator matching (not name-only)"
    rationale: "cri:intervenant elements have mat= attribute = senator matricule = actors.official_id — direct lookup replaces fragile name normalization; name fallback retained for ministers"
  - decision: "Date from filename, not XML metadata"
    rationale: "Older Senat CRI files have no dateSeance element in Metadonnees; filename dYYYYMMDD is reliable"
metrics:
  duration: "~48 minutes (34 min ingestion + 14 min tagging)"
  completed: "2026-03-30"
  debates_ingested: 413
  interventions_inserted: 292286
  actor_match_rate: "81.8%"
  tagged_interventions: 218535
  errors: 0
---

# Phase 11 Plan 04: Senat CRI Pipeline Execution Summary

**One-liner:** 413 Senat debates and 292,286 interventions ingested via cri.zip with 81.8% actor match rate using senator matricule direct lookup.

## What Was Done

Executed the Senat CRI pipeline against the real data.senat.fr bulk ZIP. The script (`ingest_debates_senat.py`) required significant bug fixes before execution — the ZIP format did not match the implementation assumptions from plan 11-02.

### Pipeline Stats
- Sessions found in ZIP for XVIIe legislature: **413**
- Debates inserted: **413**
- Interventions inserted: **292,286**
- Actor matches (senators + name fallback): **239,014 (81.8%)**
- Actor unmatched (ministers, expired mandates): **53,272 (18.2%)**
- Tagging: **218,535 tagged** out of 292,286 new Senat interventions
- Errors: **0**

### DB Verification

```sql
SELECT count(*) FROM debates WHERE chamber = 'Senat';          -- 413
SELECT count(*) FROM interventions WHERE chamber = 'Senat';    -- 292286
SELECT count(*) FROM interventions i
  JOIN intervention_tags it ON i.id = it.intervention_id
  WHERE i.chamber = 'Senat';                                    -- 218535
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Filename regex mismatch — zero sessions found**
- **Found during:** Task 1 Step 1 (--limit 5 test run)
- **Issue:** Script used `SEN_YYYYMMDD_NNN.xml` regex; actual ZIP format is `cri/dYYYYMMDD.xml`
- **Fix:** Updated `_FILENAME_RE = re.compile(r"d(\d{4})(\d{2})(\d{2})\.xml")`; updated `iter_xviie_sessions()` to yield `(filename, session_date, xml_bytes)` (date extracted at iteration time, not from XML)
- **Files modified:** `packages/ingestion/scripts/ingest_debates_senat.py`
- **Commit:** a3edd13

**2. [Rule 1 - Bug] XML parser rejected 394/413 XVIIe files as malformed**
- **Found during:** Task 1 investigation of 0 sessions found
- **Issue:** Older Senat CRI files (2022-2023) contain HTML/XML mixtures with mismatched tags (`<divers>...</div>`). Strict etree.fromstring() raises XMLSyntaxError
- **Fix:** `etree.XMLParser(recover=True, encoding="iso-8859-1")` recovers all 413 files successfully
- **Files modified:** `packages/ingestion/scripts/ingest_debates_senat.py`
- **Commit:** a3edd13

**3. [Rule 1 - Bug] Wrong XML element structure — PublicationDSenat format assumed but actual is cri:cri namespace**
- **Found during:** Task 1 investigation
- **Issue:** Script searched for `Metadonnees/dateSeance`, `ContenuDSenat/CompteRendu`, `Para/Orateur/Nom` elements. Actual format uses `cri:intervenant` elements with `nom`, `civ`, `qua`, `mat` XML attributes
- **Fix:** Rewrote `parse_senat_cri_xml()` to use `{CRI_NS}intervenant` elements and their attributes
- **Files modified:** `packages/ingestion/scripts/ingest_debates_senat.py`
- **Commit:** a3edd13

**4. [Rule 1 - Bug] Name-only matching replaced by mat-based direct lookup**
- **Found during:** Task 1 investigation of actual XML structure
- **Issue:** Plan assumed no href/ID on speakers — but `cri:intervenant` has a `mat` attribute = senator matricule which maps directly to `actors.official_id`
- **Fix:** `load_senator_cache()` now returns `(by_mat, by_name)` dict pair; `match_senator()` tries mat first, name fallback for unmatched (ministers etc.). Result: 81.8% match vs ~67% expected from name-only
- **Files modified:** `packages/ingestion/scripts/ingest_debates_senat.py`
- **Commit:** a3edd13

**5. [Rule 1 - Bug] UnboundLocalError in finally block when no sessions found**
- **Found during:** Task 1 initial test run
- **Issue:** `conn = None` was inside the try block after the early `return stats`. The `finally` block referenced `conn` which was never assigned
- **Fix:** Moved `conn = None` initialization before the `try` block
- **Files modified:** `packages/ingestion/scripts/ingest_debates_senat.py`
- **Commit:** a3edd13

## Self-Check

### Created files
- `.planning/phases/11-ingestion-debats-cri/11-04-SUMMARY.md` — this file

### Modified files
- `packages/ingestion/scripts/ingest_debates_senat.py` — bug fixes

### Commits exist
- a3edd13: fix(11-04): rewrite ingest_debates_senat.py for actual cri.zip format

### Database state
- debates WHERE chamber='Senat': 413
- interventions WHERE chamber='Senat': 292,286
- tagged Senat interventions: 218,535
- match rate: 81.8%

## Self-Check: PASSED

## Next

Task 2 (checkpoint:human-verify) — awaiting human verification of Senat debates in UI:
1. http://localhost:3000 — Senat filter tab shows Senat debates
2. Click a Senat debate — interventions display with speaker names/roles
3. Cross-chamber search returns results from both AN and Senat
