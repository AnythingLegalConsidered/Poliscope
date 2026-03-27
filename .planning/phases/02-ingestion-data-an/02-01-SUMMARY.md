---
phase: 02-ingestion-data-an
plan: 01
status: done
commits:
  - fdcb43d: "feat(02-01): Python environment + shared modules"
  - c82a200: "feat(02-01): deputy ingestion script from nosdeputes.fr"
duration: ~6 min
completed: 2026-03-27
tags: [python, ingestion, nosdeputes, deputies]
key-files:
  created:
    - scripts/requirements.txt
    - scripts/config.py
    - scripts/db.py
    - scripts/utils.py
    - scripts/ingest_deputies.py
decisions:
  - id: D-0201-01
    summary: "Python 3.12 installed via winget (was missing from system)"
  - id: D-0201-02
    summary: "nosdeputes.fr serves 16th legislature (ended) — all 618 deputies have mandat_fin, is_active=false is correct"
---

# Phase 2 Plan 01: Python env + ingestion deputes

Python ingestion environment with shared modules (config, db, utils) and deputy ingestion from nosdeputes.fr API, upserting 618 deputies into PostgreSQL.

## What was built

- **scripts/requirements.txt**: Python deps (psycopg, httpx, python-dotenv, python-slugify, tqdm, lxml)
- **scripts/config.py**: Loads .env from project root, exports DATABASE_URL, NOSDEPUTES_BASE, REQUEST_DELAY, LEGISLATURE
- **scripts/db.py**: `get_connection()` + `upsert_query()` dynamic SQL builder (handles ON CONFLICT, updated_at flag)
- **scripts/utils.py**: Logging setup, `rate_limit()`, `fetch_json()` with httpx + rate limiting
- **scripts/ingest_deputies.py**: Fetches all deputies from `/deputes/json`, maps to schema, upserts via ON CONFLICT (official_id)

## Verification results

- Config import: OK
- DB connection: OK
- Utils import: OK
- Ingestion run 1: 618 deputies fetched and upserted
- Ingestion run 2 (idempotence): 618 deputies, no duplicates
- Sample data verified: official_id, full_name, political_group present

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Python 3.12 not installed**
- **Found during:** Task 1 (pip install)
- **Issue:** No Python installation on system, Windows Store stubs only
- **Fix:** Installed Python 3.12.10 via `winget install Python.Python.3.12`
- **Impact:** None on code, required for execution

### Observations (not deviations)

**nosdeputes.fr serves the 16th legislature (2022-2024)**
- The default API (`/deputes/json`) returns 618 deputies from the previous (16th) legislature
- All have `mandat_fin` set (legislature ended June 2024), so `is_active = False` for all
- The site states: "NosDeputes.fr reviendra d'ici quelques mois avec une nouvelle version pour les deputes elus en 2024"
- This is correct behavior: these are the deputies with debate/intervention data on the platform
- When 17th legislature data becomes available, the script will correctly set `is_active = True` for those without `mandat_fin`

## Notes for next plan

- 618 deputies in DB, all from 16th legislature with is_active=false
- `official_id` is the AN ID (id_an field), used for matching interventions
- Shared modules (config, db, utils) ready for 02-02 (debate ingestion)
- `fetch_json()` follows rate limiting (1s delay) — important for debate API calls
- Python path: `C:\Users\Ianis\AppData\Local\Programs\Python\Python312\python.exe` (not on PATH in bash)

## Self-Check: PASSED

- All 5 files exist
- Both commits found (fdcb43d, c82a200)
- 618 deputies verified in database
- Idempotence verified (same count after re-run)
