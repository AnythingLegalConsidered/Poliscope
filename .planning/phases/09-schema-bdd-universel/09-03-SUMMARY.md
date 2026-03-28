---
phase: 09-schema-bdd-universel
plan: 03
subsystem: database
tags: [migration, postgresql, gap-closure, fts, drizzle]

# Dependency graph
requires:
  - phase: 09-schema-bdd-universel
    plan: 01
    provides: Hand-written migration 0001 SQL + schema.ts with actors table
  - phase: 09-schema-bdd-universel
    plan: 02
    provides: Migration 0002 SQL with 7 new tables
provides:
  - Live DB migrated: actors table with 618 rows (renamed from deputies)
  - 12 tables total in poliscope DB on 192.168.2.200
  - FTS GIN indexes confirmed via EXPLAIN ANALYZE (idx_actors_fts, idx_interventions_fts)
  - All API endpoints functional post-migration
affects:
  - 10-ingestion-an (can now INSERT into actors, organs, cross_references)
  - 11-ingestion-senat (Senat actors table ready)
  - 12-ingestion-votes (scrutins + votes tables ready)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Direct psql SSH migration when drizzle-kit migrate fails silently
    - Manual insert into drizzle.__drizzle_migrations to track applied migrations

key-files:
  modified:
    - packages/shared/drizzle/0001_rename-deputies-to-actors.sql

key-decisions:
  - "idx_interventions_fts_stored renamed to idx_interventions_fts in migration SQL — aligns with schema.ts and snapshot"
  - "DROP INDEX before CREATE INDEX (same name) to safely replace old functional index with stored column GIN index"
  - "Migrations applied via direct psql SSH (drizzle-kit migrate had silent connection failure) — migration records inserted manually"

patterns-established:
  - "For monorepo setups where drizzle-kit migrate fails: pipe SQL directly via SSH psql with ON_ERROR_STOP=1"

# Metrics
duration: 20min
completed: 2026-03-28
---

# Phase 9 Plan 03: Gap Closure — Fix index inconsistency + apply migrations

**Fix index name mismatch in migration SQL, apply migrations 0001+0002 to live poliscope-db, verify data integrity and API endpoints**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-28T17:00:00Z
- **Completed:** 2026-03-28T17:20:00Z
- **Tasks:** 2/2
- **Files modified:** 1

## Accomplishments
- Fixed index name inconsistency: `idx_interventions_fts_stored` → `idx_interventions_fts` in migration 0001 SQL
- Reordered DROP INDEX before CREATE INDEX to safely replace old functional index
- `drizzle-kit generate` confirms zero drift (schema.ts / snapshot / SQL all aligned)
- Migration 0001 applied: deputies → actors rename, tsvector columns, new indexes
- Migration 0002 applied: 7 new tables (amendments, cross_references, legislatures, organs, questions, scrutins, votes)
- Data integrity verified: actors=618, interventions=2479 — zero data loss
- FTS indexes confirmed: EXPLAIN ANALYZE shows Bitmap Index Scan on idx_actors_fts and idx_interventions_fts
- API endpoints verified: /api/deputies (618), /api/debates (5), /api/search?q=budget (4 results)

## Task Commits

1. **Task 1: Fix index name inconsistency in migration 0001 SQL** - `c905b4d` (fix)
2. **Task 2: Apply migrations to live DB and verify data integrity** - manual (psql SSH, no code commit)

## Files Created/Modified
- `packages/shared/drizzle/0001_rename-deputies-to-actors.sql` — idx_interventions_fts_stored → idx_interventions_fts, DROP before CREATE

## Deviations from Plan

- `drizzle-kit migrate` failed silently (exit code 1, spinner but no SQL executed). Root cause: likely connection pooling or auth issue between drizzle-kit postgres driver on Windows and remote PG17. Worked around by piping SQL directly via `ssh root@192.168.2.200 "su - postgres -c 'psql -d poliscope'"` with ON_ERROR_STOP=1.
- Migration records inserted manually into `drizzle.__drizzle_migrations` to keep drizzle-kit tracking in sync.
- API test initially showed 500 because old Nuxt processes were zombied on ports 3000/3001 with stale env. Fresh restart on port 3002 confirmed all endpoints working.

## Issues Encountered
- drizzle-kit migrate silent failure — applied migrations via direct psql instead
- Nuxt .env propagation: root `.env` not auto-loaded when Nuxt runs from `packages/web/`. Must export env vars before `pnpm --filter web dev`. Pre-existing issue from Phase 8 monorepo restructure.

## Verification Results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| actors count | 618 | 618 | ✓ |
| interventions count | 2479 | 2479 | ✓ |
| tables count | 12 | 12 | ✓ |
| idx_actors_fts scan | Bitmap Index Scan | Bitmap Index Scan | ✓ |
| idx_interventions_fts scan | Bitmap Index Scan | Bitmap Index Scan | ✓ |
| GET /api/deputies | 618 | 618 | ✓ |
| GET /api/debates | >0 | 5 | ✓ |
| GET /api/search?q=budget | >0 | 4 | ✓ |

---
*Phase: 09-schema-bdd-universel*
*Completed: 2026-03-28*
