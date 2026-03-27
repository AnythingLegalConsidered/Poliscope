---
phase: 02-ingestion-data-an
plan: 03
status: done
commits:
  - 6b8a383: "feat(02-03): keyword tagging dictionary and intervention tagger"
  - ea73f54: "feat(02-03): pipeline orchestrator + fix FK cascade on re-ingest"
duration: ~3 min
completed: 2026-03-27
tags: [python, tagging, keywords, pipeline, orchestrator]
key-files:
  created:
    - scripts/tags_dictionary.py
    - scripts/tag_interventions.py
    - scripts/run_all.py
  modified:
    - scripts/ingest_debates.py
decisions: []
---

# Phase 2 Plan 03: Keyword Tagging + Pipeline Orchestrator

12 thematic tag categories with keyword matching applied to parliamentary interventions, plus a single-command orchestrator for the full ingestion pipeline.

## What was built

- **scripts/tags_dictionary.py**: Static dictionary with 12 thematic categories (economie, securite, sante, education, environnement, justice, immigration, logement, transport, agriculture, numerique, culture). Exports `TAGS_DICTIONARY`, `TAGS_DISPLAY_NAMES`, and `tag_content()` function for case-insensitive keyword matching.

- **scripts/tag_interventions.py**: Tagging script that upserts 12 tags into the `tags` table, fetches untagged interventions, matches keywords via `tag_content()`, and inserts into `intervention_tags`. Batch commits per 100 interventions, tqdm progress. Supports `--retag-all` to clear and retag everything. Idempotent via `ON CONFLICT DO NOTHING`.

- **scripts/run_all.py**: Pipeline orchestrator running `ingest_deputies.py` -> `ingest_debates.py` -> `tag_interventions.py` in sequence via subprocess. Supports `--limit`, `--start-date`, `--end-date`, `--skip-deputies`, `--skip-debates`, `--skip-tags`, `--retag-all`. Final summary with DB counts and execution time.

## Verification results

- **tag_interventions.py**: 12 tags created, 2479 interventions processed, 787 tag assignments
- **DB verification**:
  - `SELECT count(*) FROM tags` = 12
  - `SELECT count(*) FROM intervention_tags` = 787
  - Top tags: Justice (315), Logement (107), Economie (93), Agriculture (69), Education (58)
  - 1916 interventions untagged (short procedural texts without thematic keywords)
- **Idempotence**: Re-run processed 1916 remaining interventions, 0 new tags assigned (correct: no keywords match)
- **run_all.py --skip-deputies --skip-debates --skip-tags**: Skips all scripts, shows summary (0 errors)
- **run_all.py --skip-deputies --limit 2**: Pipeline runs debates + tags, 0 errors, counts correct

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] psycopg3 executemany on Connection vs Cursor**
- **Found during:** Task 1 (tag_interventions.py first run)
- **Issue:** `conn.executemany()` does not exist in psycopg3; must use `cursor.executemany()`
- **Fix:** Changed `_flush_batch` to use `with conn.cursor() as cur: cur.executemany(...)`
- **Files modified:** scripts/tag_interventions.py
- **Commit:** 6b8a383

**2. [Rule 1 - Bug] FK constraint violation on debate re-ingestion**
- **Found during:** Task 2 (run_all.py pipeline test)
- **Issue:** `ingest_debates.py` deletes interventions before re-inserting, but `intervention_tags` FK references those interventions. DELETE fails with ForeignKeyViolation.
- **Fix:** Added `DELETE FROM intervention_tags WHERE intervention_id IN (SELECT id FROM interventions WHERE debate_id = %s)` before deleting interventions.
- **Files modified:** scripts/ingest_debates.py
- **Commit:** ea73f54

## Notes for next phase

- 77.3% of interventions are untagged (mostly short procedural texts like "La seance est ouverte")
- Tag dictionary can be expanded with more keywords to improve coverage
- For Phase 3 (API), tags are available for filtering interventions by theme
- `run_all.py` is the single entry point for refreshing all data

## Self-Check: PASSED
