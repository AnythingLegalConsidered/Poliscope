---
phase: 09-schema-bdd-universel
plan: 02
subsystem: database
tags: [drizzle, postgresql, tsvector, fts, migration, schema, scrutins, votes, cross-reference]

# Dependency graph
requires:
  - phase: 09-01
    provides: actors table (renamed from deputies), stored tsvector on actors + interventions, drizzle snapshot in sync
provides:
  - debates.chamber column (default 'AN') — additive, non-breaking
  - legislatures table — number, startDate, endDate, chamber
  - organs table — officialId, organType, chamber, legislatureId, parentOrganId (no FK self-ref)
  - scrutins table — officialId, date, chamber, sessionId FK->debates, legislatureId FK, result, votesFor/Against/Abstain
  - votes table — scrutinId FK cascade, actorId FK cascade, position, delegationActorId
  - questions table — questionType, stored tsvector search_vector + GIN index (schema only, no ingestion)
  - amendments table — status, actorId FK, legislatureId FK (schema only, no ingestion)
  - crossReferences table — actorId FK cascade, sourceType + sourceId pattern
  - Additive migration 0002_add-universal-schema.sql (zero DROP TABLE)
  - TypeScript types: Legislature, Organ, Scrutin, Vote, Question, Amendment, CrossReference
affects:
  - 10-ingestion-an (can now reference organs, legislatures FKs)
  - 11-ingestion-senat (can reference actors, debates, legislatures with chamber='Senat')
  - 12-ingestion-votes (scrutins + votes tables ready for data)
  - All future API phases (Phase 13+) building on complete 12-table schema

# Tech tracking
tech-stack:
  added: []
  patterns:
    - sourceType + sourceId cross-reference pattern (not per-source columns) — easier to add new sources without schema changes
    - parentOrganId without FK constraint for self-referential organs (avoids circular reference at DB level; resolved at app level)
    - questions.search_vector stored tsvector covering title + content concatenation with coalesce null guards

key-files:
  created:
    - packages/shared/drizzle/0002_add-universal-schema.sql
    - packages/shared/drizzle/meta/0002_snapshot.json
  modified:
    - packages/shared/src/schema.ts
    - packages/shared/src/types.ts
    - packages/shared/drizzle/meta/_journal.json

key-decisions:
  - "crossReferences uses sourceType + sourceId pattern (not one column per source) — easier to extend for new identifier systems"
  - "organs.parentOrganId has no DB-level FK — self-referential FK avoided to prevent circular dependency; resolved at application level"
  - "questions and amendments: schema-only, no ingestion until v3 (per ROADMAP scope decision)"

# Metrics
duration: 12min
completed: 2026-03-28
---

# Phase 9 Plan 02: Complete Universal Schema (7 new tables + chamber) Summary

**7 additive tables (legislatures, organs, scrutins, votes, questions, amendments, cross_references) + debates.chamber column — drizzle-kit generate produces zero DROP TABLE, 12-table schema complete**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-28T15:32:04Z
- **Completed:** 2026-03-28T15:44:00Z
- **Tasks:** 2/2
- **Files modified:** 5 (2 schema, 3 migration)

## Accomplishments

- Complete 12-table universal parliamentary schema covering all 8 SCHEMA-xx requirements
- debates.chamber column added (DEFAULT 'AN') — additive, no data risk
- scrutins + votes tables: prerequisite for Phase 12 (vote ingestion, #1 user priority)
- crossReferences table: sourceType/sourceId pattern enables PA → nosdeputes → DILA → Senat mapping without schema changes per new source
- questions.search_vector: stored tsvector GIN index covering title + content (FTS ready when data arrives in v3)
- Additive migration verified safe: 7 CREATE TABLE, 1 ALTER TABLE ADD COLUMN, zero DROP TABLE
- All FK constraints: votes→scrutins cascade, cross_references→actors cascade, scrutins→debates (nullable)
- TypeScript build: nuxt build passes clean (zero errors)
- drizzle-kit generate after Task 2 commit: "No schema changes, nothing to migrate" — snapshot in sync

## Task Commits

1. **Task 1: Add 7 new tables to schema + chamber on debates + TypeScript types** - `644cb0a` (feat)
2. **Task 2: Generate additive migration 0002 + verify** - `94c5afe` (feat)

## Files Created/Modified

- `packages/shared/src/schema.ts` — 12 tables (was 5): legislatures, organs, scrutins, votes, questions, amendments, crossReferences added; debates.chamber added
- `packages/shared/src/types.ts` — 15 types (was 8): Legislature, Organ, Scrutin, Vote, Question, Amendment, CrossReference added
- `packages/shared/drizzle/0002_add-universal-schema.sql` — Additive migration: 7 CREATE TABLE + 1 ALTER TABLE + 12 FK constraints + 22 indexes (GIN + btree)
- `packages/shared/drizzle/meta/0002_snapshot.json` — Post-migration drizzle snapshot (12 tables)
- `packages/shared/drizzle/meta/_journal.json` — Updated with 0002 migration entry

## SCHEMA-xx Requirements Coverage

| Requirement | Status | Tables |
|-------------|--------|--------|
| SCHEMA-01: acteurs, organes, legislatures | DONE | actors, organs, legislatures |
| SCHEMA-02: seances, interventions avec chambre | DONE | debates.chamber, interventions.chamber |
| SCHEMA-03: scrutins et votes | DONE | scrutins, votes |
| SCHEMA-04: questions | DONE (schema only) | questions |
| SCHEMA-05: amendements | DONE (schema only) | amendments |
| SCHEMA-06: cross-reference | DONE | cross_references |
| SCHEMA-07: migration sans perte | DONE | 0001 rename + 0002 additive, no DROP TABLE |
| SCHEMA-08: index FTS | DONE | GIN on actors.search_vector, interventions.search_vector, questions.search_vector |

## Decisions Made

- `crossReferences` uses `sourceType + sourceId` (2 columns) rather than one column per source system — adding a new identifier source only requires a new row, not a schema change.
- `organs.parentOrganId` deliberately has no FK constraint — self-referential FKs can cause circular dependency issues at insert time; resolved at application level instead.
- `questions` and `amendments` tables created schema-only with no ingestion scripts — deferred to v3 per ROADMAP scope decision (votes are the #1 priority for v2).

## Deviations from Plan

None — plan executed exactly as written. drizzle-kit generate produced the exact expected output on first run.

## User Setup Required

None. Migration SQL is ready to apply on LXC poliscope-db (PG17) via:
```bash
pnpm --filter shared drizzle-kit migrate
```

## Next Phase Readiness

- Complete 12-table schema ready for Phase 10 (ingestion AN)
- Phase 12 (votes) structural prerequisite met: scrutins + votes tables defined with correct FK cascade
- crossReferences table ready for Phase 10/11 to populate actor identifier mappings
- drizzle snapshot in sync — future `drizzle-kit generate` correctly detects only true deltas

---

## Self-Check: PASSED

- [x] `packages/shared/src/schema.ts` exists — 12 pgTable() calls confirmed
- [x] `packages/shared/src/types.ts` exists — 15 exported types confirmed
- [x] `packages/shared/drizzle/0002_add-universal-schema.sql` exists — 7 CREATE TABLE, 0 DROP TABLE
- [x] `packages/shared/drizzle/meta/0002_snapshot.json` exists
- [x] Commit 644cb0a exists (Task 1)
- [x] Commit 94c5afe exists (Task 2)
- [x] TypeScript build: nuxt build passed clean

---
*Phase: 09-schema-bdd-universel*
*Completed: 2026-03-28*
