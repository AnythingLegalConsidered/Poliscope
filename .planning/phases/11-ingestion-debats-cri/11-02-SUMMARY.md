---
phase: 11-ingestion-debats-cri
plan: "02"
subsystem: ingestion
tags:
  - python
  - senat
  - xml
  - debates
  - interventions
dependency_graph:
  requires:
    - "10-01 actors table (chamber='Senat' rows must exist for senator matching)"
    - "09-02 debates + interventions tables with chamber column"
  provides:
    - "ingest_debates_senat.py — Senat CRI ingestion pipeline"
    - "run_all.py 9-step orchestrator"
  affects:
    - "debates table (Senat rows)"
    - "interventions table (Senat rows, actor_id matched by name)"
tech_stack:
  added: []
  patterns:
    - "httpx.stream() to temp file for large ZIP downloads (avoids OOM)"
    - "zipfile.ZipFile on temp file for per-session XML iteration"
    - "Name-only senator matching via normalize_name() — no href/ID in Senat XML"
    - "Timezone-stripped dateSeance parsing (re.sub [+-]\\d{2}:\\d{2}$)"
key_files:
  created:
    - packages/ingestion/scripts/ingest_debates_senat.py
  modified:
    - packages/ingestion/scripts/run_all.py
decisions:
  - "Stream cri.zip to temp file: httpx.stream() + NamedTemporaryFile(delete=False) — not httpx.get().content which would OOM on 510 MB"
  - "Name-only senator matching: Senat XML has no href on Orateur — cross_references not viable for CRI"
  - "XVIIE_START = 2022-06-22: matches AN legislature start for consistent scope"
  - "legislature=17 hardcoded: Senat has no discrete legislature numbering, 17 aligns with AN XVIIe"
  - "Import _clean_unicode + _extract_speech_content + normalize_name from ingest_debates.py: avoids duplication"
metrics:
  duration: "4 minutes"
  completed: "2026-03-30"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 11 Plan 02: Senat CRI Ingestion Pipeline Summary

**One-liner:** Senat CRI pipeline from data.senat.fr cri.zip — streaming 510 MB ZIP, parsing PublicationDSenat XML, name-only senator matching, chamber='Senat' on debates + interventions.

## What Was Built

### Task 1: ingest_debates_senat.py (NEW — 620 lines)

Complete Senat CRI ingestion pipeline:

- `download_cri_zip_to_temp()`: streams cri.zip via `httpx.stream()` to `tempfile.NamedTemporaryFile` — avoids loading 510 MB into RAM on the 4GB LXC
- `iter_xviie_sessions(zip_path, start_date)`: iterates `zipfile.ZipFile`, filters by filename pattern `SEN_YYYYMMDD_NNN.xml`, yields sessions on or after `start_date`
- `_strip_tz(date_str)`: strips timezone offset from Senat XML dates (`"2024-01-15+01:00"` → `"2024-01-15"`) using `re.sub(r"[+-]\d{2}:\d{2}$", "", date_str)`
- `parse_senat_cri_xml(xml_bytes)`: parses `PublicationDSenat` root, extracts `Metadonnees/dateSeance`, `numParution`, iterates `Para/Orateur/Nom` for interventions, reads role from `Orateur/Qualite`
- `load_senator_cache(conn)`: queries `actors WHERE chamber = 'Senat'`, builds name → id dict
- `match_senator(speaker_name, by_name)`: strips civility prefix (M., Mme), normalizes, looks up in cache
- `upsert_debate()` + `insert_interventions()`: reuse db.py patterns with `chamber='Senat'`
- Official ID format: `SEN-YYYY-MM-DD-NNN` (e.g. `SEN-2024-01-15-001`)
- Stats tracking: debates_processed, interventions_inserted, actor_matches, actor_unmatched, errors

CLI: `--limit`, `--start-date`, `--dry-run`, `--senat-zip-path`, `--log-unmatched`

### Task 2: run_all.py (UPDATED — 9-step pipeline)

- Renamed Step 7 to "ingest_debates.py (AN CRI)" for clarity
- Added Step 8: "ingest_debates_senat.py (Senat CRI)" with `--skip-senat-debates` flag
- Renamed old Step 8 (tags) to Step 9
- Added `--senat-zip-path` argument passed through to ingest_debates_senat.py
- Updated docstring to show 9-step pipeline

## Verification Results

| Check | Result |
|-------|--------|
| `python -c "import ingest_debates_senat"` | PASS |
| `run_all.py --help` shows `--skip-senat-debates` | PASS |
| `run_all.py --help` shows `--senat-zip-path` | PASS |
| Streaming download (httpx.stream + NamedTemporaryFile) | PASS |
| Timezone stripping (re.sub pattern) | PASS |
| chamber='Senat' on debates | PASS (line 491) |
| chamber='Senat' on interventions | PASS (line 387) |
| Senator matching is name-only (no href) | PASS |

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1 | 4cb2728 | feat(11-02): create ingest_debates_senat.py — Senat CRI pipeline |
| Task 2 | 04e7883 | feat(11-02): update run_all.py orchestrator — 9-step pipeline with Senat debates |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `packages/ingestion/scripts/ingest_debates_senat.py` — FOUND
- `packages/ingestion/scripts/run_all.py` — FOUND (modified)
- Commit 4cb2728 — FOUND
- Commit 04e7883 — FOUND
