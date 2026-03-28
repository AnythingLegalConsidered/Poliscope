---
phase: 09-schema-bdd-universel
plan: 01
subsystem: database
tags: [drizzle, postgresql, tsvector, fts, migration, schema]

# Dependency graph
requires:
  - phase: 08-monorepo
    provides: pnpm monorepo with packages/shared and packages/web, shared schema importable as 'shared/schema'
provides:
  - Hand-written safe rename migration 0001_rename-deputies-to-actors.sql
  - actors table (renamed from deputies) with actor_type, chamber, legislature, stored tsvector search_vector
  - interventions.actor_id FK (renamed from deputy_id), stored tsvector search_vector, chamber column
  - Inferred TypeScript types: Actor, NewActor, Debate, Intervention, Tag
  - All 6 API routes importing exclusively from shared/schema
affects:
  - 09-02 (Plan 02 — new tables organs/scrutins/votes depend on actors existing)
  - 10-ingestion-an (ingestion scripts reference actors table)
  - 11-ingestion-senat (Senat ingestion references actors)
  - 12-ingestion-votes (votes FK references actors)

# Tech tracking
tech-stack:
  added: [customType (drizzle-orm/pg-core), tsvector stored generated columns]
  patterns:
    - Hand-written drizzle-kit --custom migration to prevent DROP TABLE on rename
    - Manual snapshot update in drizzle/meta to keep drizzle-kit in sync after hand-written migration
    - customType tsvector for stored GENERATED ALWAYS AS FTS columns
    - All API routes import schema from 'shared/schema' (never from local db/schema)
    - Backward-compatible API responses (deputyId/deputyName in JSON) while Drizzle internals use actorId

key-files:
  created:
    - packages/shared/drizzle/0001_rename-deputies-to-actors.sql
    - packages/shared/drizzle/meta/0001_snapshot.json
  modified:
    - packages/shared/src/schema.ts
    - packages/shared/src/types.ts
    - packages/web/server/api/deputies/index.get.ts
    - packages/web/server/api/deputies/[id].get.ts
    - packages/web/server/api/debates/[id].get.ts
    - packages/web/server/api/debates/index.get.ts
    - packages/web/server/api/search.get.ts
    - packages/web/server/api/__sitemap__/urls.ts
  deleted:
    - packages/web/server/db/schema.ts

key-decisions:
  - "drizzle-kit --custom flag creates empty SQL + snapshot copy — hand-write SQL, then manually update snapshot to post-migration state"
  - "Snapshot generated column expressions need table-qualified names (actors.full_name not full_name) to match drizzle-kit output"
  - "API response fields (deputyId, deputyName, etc.) kept as-is for backward compat — only Drizzle builder references change"

patterns-established:
  - "For table renames: use --custom, hand-write ALTER TABLE RENAME, manually update 0001_snapshot.json to avoid DROP/CREATE"
  - "tsvector stored columns use customType + generatedAlwaysAs with table-qualified SQL expressions"

# Metrics
duration: 30min
completed: 2026-03-28
---

# Phase 9 Plan 01: Rename deputies->actors + stored tsvector FTS columns Summary

**Hand-written safe rename migration (deputies->actors), stored tsvector GIN indexes on actors and interventions, shared schema as single source of truth for all 6 API routes**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-28T15:00:00Z
- **Completed:** 2026-03-28T15:29:00Z
- **Tasks:** 2/2
- **Files modified:** 10 (2 created, 7 modified, 1 deleted)

## Accomplishments
- Hand-written rename migration is safe: zero DROP TABLE — uses ALTER TABLE RENAME + ALTER INDEX RENAME + ALTER SEQUENCE RENAME
- actors table has stored tsvector search_vector (GIN idx_actors_fts) + actor_type/chamber/legislature columns
- interventions.actor_id FK, stored tsvector search_vector (GIN idx_interventions_fts_stored), old functional index dropped
- Drizzle snapshot manually updated to post-migration state — `drizzle-kit generate` produces "No schema changes, nothing to migrate"
- All 6 API routes import exclusively from `shared/schema`, packages/web/server/db/schema.ts deleted
- TypeScript build: nuxt build passes clean (zero errors, 193 modules transformed)

## Task Commits

1. **Task 1: Hand-write rename migration + update shared schema with actors + tsvector** - `6a000d3` (feat)
2. **Task 2: Delete web schema duplicate + update all API routes to use shared/schema** - `371a23c` (feat)

## Files Created/Modified
- `packages/shared/drizzle/0001_rename-deputies-to-actors.sql` - Safe hand-written rename migration (ALTER TABLE RENAME, no DROP TABLE)
- `packages/shared/drizzle/meta/0001_snapshot.json` - Post-migration drizzle snapshot (actors, actor_id, tsvector columns)
- `packages/shared/drizzle/meta/_journal.json` - Updated with migration entry
- `packages/shared/src/schema.ts` - actors table with tsvector customType, actorId FK on interventions, new columns
- `packages/shared/src/types.ts` - Actor, NewActor, Debate, NewDebate, Intervention, NewIntervention, Tag types
- `packages/web/server/api/deputies/index.get.ts` - imports actors from shared/schema
- `packages/web/server/api/deputies/[id].get.ts` - interventions.actorId, actors table
- `packages/web/server/api/debates/[id].get.ts` - leftJoin actors, actorId refs
- `packages/web/server/api/debates/index.get.ts` - import from shared/schema
- `packages/web/server/api/search.get.ts` - raw SQL updated: actors table, actor_id column
- `packages/web/server/api/__sitemap__/urls.ts` - actors replaces deputies in query

## Decisions Made
- Used `drizzle-kit --custom` which creates an empty SQL + snapshot copy. Hand-wrote all ALTER statements in the SQL, then manually updated `0001_snapshot.json` to reflect post-migration state with qualified column names (`"actors"."full_name"` not `"full_name"`) — this is what drizzle-kit generates internally for GENERATED ALWAYS AS expressions.
- API response field names (`deputyId`, `deputyName`, `deputyGroup`, etc.) kept unchanged for backward compatibility. Frontend routes (`/deputies/:id`) also unchanged. Only internal Drizzle ORM references changed.
- Renamed `deputyFilter` variable to `actorFilter` in search.get.ts for internal clarity, but public API param `?deputyId=` kept unchanged.

## Deviations from Plan

None — plan executed exactly as written. The only discovery was the snapshot qualified-name format for GENERATED ALWAYS AS expressions (caught by running `drizzle-kit generate` after initial snapshot update — fixed by matching drizzle-kit's output format).

## Issues Encountered
- Drizzle-kit snapshot format for GENERATED ALWAYS AS columns requires table-qualified column references (`"actors"."full_name"`) not unqualified (`"full_name"`). Discovered by running `drizzle-kit generate` after initial snapshot update, which produced a DROP/ADD cycle for the tsvector columns. Fixed by matching the exact expression format drizzle-kit outputs.

## User Setup Required
None — no external service configuration required. Migration SQL is ready to run on the LXC poliscope-db (PG17) when the team decides to apply it.

## Next Phase Readiness
- actors table schema defined and migration SQL ready — Plan 02 (organs, scrutins, votes, cross_references tables) can proceed
- Drizzle snapshot is in sync — future `drizzle-kit generate` runs will correctly detect only new deltas
- All API routes functional with new shared schema — no regression expected after migration is applied

---
*Phase: 09-schema-bdd-universel*
*Completed: 2026-03-28*
