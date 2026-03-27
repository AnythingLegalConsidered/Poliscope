---
phase: 02-ingestion-data-an
plan: 02
status: done
commits:
  - be82fa2: "feat(02-02): debate + intervention ingestion from DILA open data"
duration: ~10 min
completed: 2026-03-27
tags: [python, ingestion, dila, debates, interventions, xml]
key-files:
  created:
    - scripts/ingest_debates.py
decisions:
  - id: D-0202-01
    summary: "Pivoted from nosdeputes.fr to DILA (echanges.dila.gouv.fr) for debate data — nosdeputes.fr /seances/json returns empty for 17th legislature"
  - id: D-0202-02
    summary: "DILA CRI XML format: .taz (tar-in-tar) archives, CRI_*.xml has CompteRendu with Orateur href for deputy matching"
---

# Phase 2 Plan 02: Debate + Intervention Ingestion

DILA CRI XML ingestion pipeline parsing AN debate transcripts (.taz archives) into debates and interventions tables, with deputy matching via AN fiche ID (href) and name fallback.

## What was built

- **scripts/ingest_debates.py** (450+ lines): Full debate + intervention ingestion pipeline
  - Downloads .taz archives from DILA open data (echanges.dila.gouv.fr)
  - Extracts CRI (Compte Rendu Integral) XML from nested tar archives
  - Parses XML with lxml: metadata (date, legislature, session), speakers (Orateur with href), speech content (Para elements)
  - Deputy matching: primary via AN fiche ID extracted from Orateur href, fallback via normalized name matching
  - Upserts debates (ON CONFLICT official_id), delete+reinsert interventions per debate (idempotent)
  - CLI: `--limit N`, `--start-date`, `--end-date`, `--dry-run`, `--years`
  - tqdm progress bar, per-session error handling, final stats summary

## Verification results

- **Dry-run** (`--dry-run --limit 2`): 2 sessions parsed, 1042 interventions found, 834 deputy matches (80%)
- **Real ingestion** (`--limit 5`): 5 debates, 2479 interventions inserted, 0 errors
- **DB verification**:
  - `SELECT count(*) FROM debates` = 5
  - `SELECT count(*) FROM interventions` = 2479
  - Debates have titles, dates, legislature, source_url
  - Interventions linked to debates (debate_id FK), ordered (1 to N per debate)
  - 2124/2479 interventions (85.7%) matched to deputies via deputy_id
  - "Mme la presidente" correctly matched to different deputies via href
- **Idempotence**: Re-run with `--limit 5` produced identical counts (5 debates, 2479 interventions)

## Data source

- **Source**: DILA open data at `https://echanges.dila.gouv.fr/OPENDATA/Debats/AN/{year}/`
- **Format**: .taz files (tar containing tar containing CRI_*.xml + AAA_*.xml)
- **Available**: 102 files for 2024, 142 for 2025, 13 for 2026 (257 total)
- **Legislature**: Files span 16th and 17th legislatures (2024-01 to 2026-03)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] nosdeputes.fr seances API returns empty data**
- **Found during:** Task 1 (API exploration before writing script)
- **Issue:** All nosdeputes.fr /seances/json endpoints return `{}` for the 17th legislature (confirmed: /seances/json, /16/seances/json, date-range variants, search API)
- **Fix:** Pivoted to DILA open data (echanges.dila.gouv.fr) which has CRI XML archives for all sessions. Same data, different format (XML vs JSON), richer content (full transcript with speaker identification via AN IDs)
- **Impact:** Script uses lxml XML parsing instead of JSON; downloads .taz archives instead of REST API calls; deputy matching uses AN fiche ID from href attributes instead of nosdeputes.fr IDs
- **Files modified:** scripts/ingest_debates.py (created with DILA approach from scratch)
- **Commit:** be82fa2

### Observations

**Deputy matching rate: 85.7%**
- 14.3% unmatched speakers include: ministers (not in deputies table), "Mme la presidente" without href, procedural speakers
- Matching works well for actual deputies via both href ID and name normalization
- The 618 deputies in cache are from 16th legislature (nosdeputes.fr); 17th legislature debates may have new deputies not yet in DB

**Data overlap: 16th and 17th legislature**
- DILA 2024 files contain sessions from both legislatures (16th ended June 2024, 17th started July 2024)
- Legislature number correctly extracted from XML metadata (LegislatureNumero)
- The --start-date and --years filters allow targeting specific periods

## Notes for next plan

- 257 .taz files available across 2024-2026 (can ingest all with `--limit` removed)
- DILA updates weekly; re-running the script is safe (idempotent)
- Deputy cache should be refreshed when 17th legislature deputies are added to improve match rate
- lxml dependency already in requirements.txt (installed in 02-01)
- Intervention content is clean text (XML tags stripped), no HTML
- Speaker roles extracted from QualiteMouvement XML elements

## Self-Check: PASSED
