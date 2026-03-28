# Phase 9: Schema BDD Universel - Research

**Researched:** 2026-03-28
**Domain:** PostgreSQL schema design + Drizzle ORM migrations (deputies → actors rename, new tables, FTS)
**Confidence:** HIGH

---

## Summary

This phase extends the existing 5-table Poliscope schema into a universal parliamentary schema
covering actors, organs, sessions, votes, cross-references, and French FTS. The most critical
and risky operation is renaming `deputies` → `actors` with live data (618 rows, 2479 FK-dependent
interventions). Everything else is additive.

The current schema already has a valid Drizzle setup (`drizzle-orm 0.45.1`, `drizzle-kit 0.31.10`)
with a single generated migration (`0000_luxuriant_guardian.sql`). The existing FTS uses a
functional GIN index (`to_tsvector(...)` expression), but the decision is to move to a stored
generated column (`GENERATED ALWAYS AS ... STORED`) for actors and interventions — this is the
current PostgreSQL 17 best practice confirmed by official docs and eliminates the
`to_tsvector()` recalculation on index verification.

The web server has a schema duplication problem: `packages/web/server/db/schema.ts` is a copy of
`packages/shared/src/schema.ts`. After this phase, all API routes must import from `shared/schema`
exclusively. Eight API route files reference `deputies` or `interventions` by name — they all
need updating when `deputies` is renamed to `actors`.

**Primary recommendation:** Hand-write the rename migration as a custom SQL file. Never let
drizzle-kit auto-detect a table rename on production data — it risks generating DROP TABLE. Use
`drizzle-kit generate --custom --name=rename-deputies-to-actors` then write the ALTER TABLE
RENAME TO SQL manually.

---

## Standard Stack

### Core (already installed, no changes needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| drizzle-orm | 0.45.1 | ORM query builder | Already in use, stable |
| drizzle-kit | 0.31.10 | Schema diffing + migration generation | Already in use |
| postgres | 3.4.8 | PostgreSQL driver | Already in use |

### Features Used in This Phase

| Feature | API | Source |
|---------|-----|--------|
| `customType` | `import { customType } from 'drizzle-orm/pg-core'` | Needed for `tsvector` column type |
| `generatedAlwaysAs()` | Column method | Stored generated column for FTS |
| `--custom` flag | `drizzle-kit generate --custom` | Hand-written migration file |
| `pgTable` with `index().using('gin', ...)` | Table definition | GIN index on tsvector column |

### No New Packages Required

All required packages are already installed in `packages/shared/package.json` and
`packages/web/package.json`. No `pnpm install` needed for this phase.

---

## Architecture Patterns

### Schema File Structure (packages/shared/src/)

```
packages/shared/src/
├── schema.ts          # Single source of truth — ALL tables defined here
├── types.ts           # TypeScript inferred types (currently empty, will grow)
└── index.ts           # Re-exports schema + types
```

The `packages/web/server/db/schema.ts` is a legacy duplicate. It MUST be deleted and replaced
with imports from `shared/schema` after this phase.

### Pattern 1: Stored Generated tsvector Column (Drizzle + PostgreSQL 17)

**What:** A column defined with `GENERATED ALWAYS AS (...) STORED` — PostgreSQL auto-maintains it
on every INSERT/UPDATE. No triggers needed.

**When to use:** Any column that requires FTS on text content that changes over time.

**Verified pattern (from official Drizzle docs — orm.drizzle.team/docs/guides/full-text-search-with-generated-columns):**

```typescript
// Source: https://orm.drizzle.team/docs/guides/full-text-search-with-generated-columns
import { SQL, sql } from 'drizzle-orm'
import { customType, index, pgTable, text, integer } from 'drizzle-orm/pg-core'

// Step 1: define tsvector as a custom type
const tsvector = customType<{ data: string }>({
  dataType() {
    return 'tsvector'
  },
})

// Step 2: use .generatedAlwaysAs() on the column
export const actors = pgTable('actors', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  fullName: text('full_name').notNull(),
  // single-column FTS
  searchVector: tsvector('search_vector')
    .generatedAlwaysAs((): SQL => sql`to_tsvector('french', ${actors.fullName})`),
}, (t) => [
  index('idx_actors_fts').using('gin', t.searchVector),
])
```

This generates in SQL:
```sql
"search_vector" tsvector GENERATED ALWAYS AS (to_tsvector('french', "full_name")) STORED
CREATE INDEX idx_actors_fts ON actors USING gin (search_vector);
```

**Multi-column variant** (for interventions — content is the main field):

```typescript
// Source: https://orm.drizzle.team/docs/guides/full-text-search-with-generated-columns
searchVector: tsvector('search_vector')
  .generatedAlwaysAs(
    (): SQL => sql`to_tsvector('french', ${interventions.content})`
  ),
```

**Query pattern using the stored vector:**

```sql
-- Use the column directly — no to_tsvector() recalculation
SELECT * FROM interventions
WHERE search_vector @@ websearch_to_tsquery('french', $1)
ORDER BY ts_rank(search_vector, websearch_to_tsquery('french', $1)) DESC
```

### Pattern 2: Table Rename Migration (deputies → actors)

**What:** Renames the table, preserves ALL data and sequences. DO NOT let drizzle-kit auto-detect this.

**Why hand-write:** drizzle-kit may interpret a renamed table as DROP + CREATE, which would destroy
all 618 deputies. This risk is noted in the prior decisions. The safe path is a custom migration.

**Workflow:**

```bash
# Step 1: generate an empty custom migration file
cd packages/shared
pnpm db:generate -- --custom --name=rename-deputies-to-actors
```

This creates `packages/shared/drizzle/0001_rename-deputies-to-actors.sql`.

**Write this SQL in the file:**

```sql
-- Rename table
ALTER TABLE "deputies" RENAME TO "actors";

-- Rename the sequence (GENERATED ALWAYS AS IDENTITY uses a sequence)
ALTER SEQUENCE "deputies_id_seq" RENAME TO "actors_id_seq";

-- Rename the unique constraint
ALTER TABLE "actors" RENAME CONSTRAINT "deputies_official_id_unique" TO "actors_official_id_unique";

-- Rename the FK constraint on interventions (references deputies.id)
ALTER TABLE "interventions" RENAME CONSTRAINT "interventions_deputy_id_deputies_id_fk"
  TO "interventions_actor_id_actors_id_fk";

-- Rename the column on interventions (deputy_id → actor_id)
ALTER TABLE "interventions" RENAME COLUMN "deputy_id" TO "actor_id";
```

**Then update the TypeScript schema** to use the new table name before running drizzle-kit generate
for subsequent additive tables (so the snapshot stays in sync).

### Pattern 3: Additive Tables (safe, no data risk)

All new tables (organs, legislatures, sessions, scrutins, votes, questions, amendments,
cross_references) are additive — they don't touch existing data. Generate normally:

```bash
pnpm db:generate -- --name=add-organs-legislatures
pnpm db:generate -- --name=add-sessions
pnpm db:generate -- --name=add-cross-references
# etc.
```

Or batch all new tables into a single migration after the rename migration is applied.

### Pattern 4: cross_references Table Design

The cross_references table maps actor identifiers between three sources:

| Source | ID Format | Example |
|--------|-----------|---------|
| AN Official (PA) | `PA` + numeric | `PA795746` |
| DILA CRI href | numeric only | `795746` (from `/fiches_id/795746.asp`) |
| nosdeputes.fr slug | kebab-case | `francois-bayrou` |
| Sénat | numeric | TBD (phase future) |

**Minimal design for v2:**

```typescript
export const crossReferences = pgTable('cross_references', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  actorId: integer('actor_id').references(() => actors.id, { onDelete: 'cascade' }),
  sourceType: text('source_type').notNull(), // 'PA', 'nosdeputes_slug', 'dila_href', 'senat'
  sourceId: text('source_id').notNull(),     // the raw identifier value
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => [
  index('idx_cross_ref_actor').on(t.actorId),
  index('idx_cross_ref_source').on(t.sourceType, t.sourceId),
])
```

This is simpler than one column per source — easier to add new sources without schema changes.

### Recommended New Tables (with scope notes)

| Table | Status | Notes |
|-------|--------|-------|
| `actors` | REQUIRED — rename from `deputies` | 618 rows, HIGH risk |
| `cross_references` | REQUIRED (SCHEMA-06) | Empty initially |
| `organs` | REQUIRED (SCHEMA-01) | Groupes, commissions — empty initially |
| `legislatures` | REQUIRED (SCHEMA-01) | Simple lookup table |
| `sessions` / `seances` | REQUIRED (SCHEMA-02) | Could be current `debates` table evolved |
| `scrutins` | REQUIRED (SCHEMA-03) | Empty initially |
| `votes` | REQUIRED (SCHEMA-03) | Ingested phase 12 |
| `questions` | REQUIRED (SCHEMA-04) | Schema only, no ingestion |
| `amendments` | REQUIRED (SCHEMA-05) | Schema only, no ingestion |

Note: `debates` table may stay (CRI sessions), but needs a `chamber` column (`AN`/`Senat`).

### Anti-Patterns to Avoid

- **Never** run `pnpm db:generate` after renaming deputies → actors in TypeScript without first
  verifying the custom migration is in place. Drizzle-kit will see the table as "gone" and generate
  DROP TABLE.
- **Never** use `pnpm db:push` on production data. Push is for prototyping only.
- **Never** modify the generated snapshot JSON files manually — drizzle-kit owns them.
- **Never** use functional GIN index (`USING gin (to_tsvector(...))`) for the new schema. Use stored
  generated columns instead — it is the current best practice per PostgreSQL 17 official docs.
- **Never** let the web package `server/db/schema.ts` diverge from `shared/schema.ts`. Delete
  the duplicate and import from `shared/schema`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FTS auto-update on INSERT/UPDATE | Triggers manually | `GENERATED ALWAYS AS ... STORED` + GIN | PostgreSQL 17 native, zero maintenance |
| Migration diffing | Custom diff scripts | `drizzle-kit generate` | Handles all DDL except renames |
| Data migration from deputies → actors | Python script | Custom SQL in migration file | Atomic, transactional, no Python dependency |
| Cross-reference lookups | Multiple join tables | Single `cross_references` with `source_type` | One table handles all ID sources |
| Type safety for schema | Manual TypeScript interfaces | Drizzle `InferSelectModel<typeof actors>` | Auto-generated from schema, zero drift |

**Key insight:** Drizzle's `generatedAlwaysAs()` with `customType` for tsvector is the correct
idiom in 2026. The old pattern (functional GIN index) still works but requires
`to_tsvector()` recalculation on every index verification. Stored columns avoid this.

---

## Common Pitfalls

### Pitfall 1: drizzle-kit generates DROP TABLE for renamed table

**What goes wrong:** You rename `deputies` → `actors` in `schema.ts`, run `drizzle-kit generate`,
drizzle-kit sees no table called `deputies` in the new schema and no table called `actors` in the
snapshot, so it generates `DROP TABLE deputies; CREATE TABLE actors`. This deletes all 618 deputies.

**Why it happens:** Drizzle-kit does prompt for renames interactively, but this behavior is not
reliable in CI/non-interactive contexts, and the prompt can be accidentally dismissed. Confirmed
by GitHub issues (#2533, #3826) where rename detection fails.

**How to avoid:** Always use `--custom` for the rename migration. Write `ALTER TABLE deputies
RENAME TO actors` manually. Update the snapshot by running `drizzle-kit generate` AFTER the
custom migration is applied (with the already-renamed TypeScript schema in place).

**Warning signs:** Generated SQL contains `DROP TABLE "deputies"` — STOP immediately.

### Pitfall 2: Stored generated column references self (circular)

**What goes wrong:** PostgreSQL forbids a generated column from referencing another generated
column. If `search_vector` depends on a computed column, the migration fails.

**Why it happens:** Only applies to multi-column FTS that combines a generated column with text.
Not a risk for our schema since `content`, `full_name` are plain text columns.

**How to avoid:** Always reference source text columns, never other generated columns.

### Pitfall 3: Interventions FK still points to `deputies` after rename

**What goes wrong:** The FK `interventions.deputy_id → deputies.id` remains after table rename.
PostgreSQL automatically follows the table rename for FKs (the constraint updates automatically),
but the COLUMN NAME `deputy_id` does not rename automatically — it stays as `deputy_id`.

**How to avoid:** Explicitly rename the column in the custom migration:
`ALTER TABLE interventions RENAME COLUMN deputy_id TO actor_id`.
This is already included in the Pattern 2 migration SQL above.

**Warning signs:** Post-migration, `\d interventions` still shows `deputy_id` — means column
rename was not executed.

### Pitfall 4: Duplicate schema between web and shared

**What goes wrong:** `packages/web/server/db/schema.ts` is a copy of the shared schema. After
adding new tables to `shared/schema.ts`, the web package API routes still import from the stale
local copy and can't access new tables.

**Why it happens:** The web package's `db.ts` imports `import * as schema from 'shared/schema'`
(correct), but individual API route files import from `'../../db/schema'` (incorrect copy).

**How to avoid:** Delete `packages/web/server/db/schema.ts`. Update all 8 API route files to
import directly from `'shared/schema'`. Verify: `grep -r "from '../../db/schema'" packages/web/`.

**Warning signs:** TypeScript errors about missing exported table names after adding new tables
to shared schema, despite the tables being present in shared.

### Pitfall 5: FTS index migration fails on non-null stored column with existing data

**What goes wrong:** Adding a `NOT NULL` stored generated column to an existing table with rows
works in PostgreSQL 17 (the column is immediately computed), but if the expression references
a nullable column, the entire column may be NULL for existing rows.

**Why it happens:** `to_tsvector('french', NULL)` returns NULL. If `full_name` has any NULL
values, the generated column will be NULL.

**How to avoid:** Either (a) don't mark the generated column as NOT NULL, or (b) verify that
source columns are NOT NULL before migration. In our schema, `full_name` and `content` are
`NOT NULL` already — safe.

**Warning signs:** After migration, `SELECT count(*) FROM actors WHERE search_vector IS NULL`
returns > 0.

### Pitfall 6: drizzle-kit snapshot out of sync after hand-written migration

**What goes wrong:** After applying a custom SQL migration (rename), the drizzle-kit snapshot
still thinks the table is named `deputies`. The next `drizzle-kit generate` will generate a
second DROP/CREATE.

**Why it happens:** Custom migrations bypass snapshot diffing.

**How to avoid:** After applying the hand-written rename migration, the TypeScript schema
must already use the new name (`actors`). Run `drizzle-kit generate` with the new schema — if
drizzle-kit is properly tracking the custom migration in its journal, it will not re-generate
the rename. Verify by inspecting the generated SQL before applying.

---

## Code Examples

Verified patterns from official sources:

### Custom tsvector type definition (reusable across tables)

```typescript
// Source: https://orm.drizzle.team/docs/guides/full-text-search-with-generated-columns
import { customType } from 'drizzle-orm/pg-core'
import { SQL, sql } from 'drizzle-orm'

// Define once, use in multiple tables
export const tsvector = customType<{ data: string }>({
  dataType() {
    return 'tsvector'
  },
})
```

### actors table (renamed from deputies, with FTS)

```typescript
// Source: pattern from https://orm.drizzle.team/docs/generated-columns
export const actors = pgTable('actors', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),  // AN numeric ID
  firstName: text('first_name').notNull(),
  lastName: text('last_name').notNull(),
  fullName: text('full_name').notNull(),
  actorType: text('actor_type').notNull().default('deputy'), // 'deputy' | 'senator' | 'minister'
  chamber: text('chamber'),                                   // 'AN' | 'Senat'
  group: text('political_group'),
  photoUrl: text('photo_url'),
  constituency: text('constituency'),
  isActive: boolean('is_active').default(true),
  legislature: integer('legislature'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
  // Stored generated column — auto-maintained by PostgreSQL
  searchVector: tsvector('search_vector')
    .generatedAlwaysAs((): SQL => sql`to_tsvector('french', coalesce(${actors.fullName}, ''))`),
}, (t) => [
  index('idx_actors_fts').using('gin', t.searchVector),
  index('idx_actors_type').on(t.actorType),
  index('idx_actors_active').on(t.isActive),
])
```

### interventions table (with stored FTS + actor FK)

```typescript
export const interventions = pgTable('interventions', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  sessionId: integer('session_id').notNull().references(() => sessions.id),
  actorId: integer('actor_id').references(() => actors.id),  // renamed from deputy_id
  speakerName: text('speaker_name').notNull(),
  speakerRole: text('speaker_role'),
  content: text('content').notNull(),
  orderInDebate: integer('order_in_debate').notNull(),
  chamber: text('chamber').default('AN'),  // 'AN' | 'Senat'
  createdAt: timestamp('created_at').defaultNow().notNull(),
  // Stored generated FTS column
  searchVector: tsvector('search_vector')
    .generatedAlwaysAs((): SQL => sql`to_tsvector('french', ${interventions.content})`),
}, (t) => [
  index('idx_interventions_session').on(t.sessionId),
  index('idx_interventions_actor').on(t.actorId),
  index('idx_interventions_fts').using('gin', t.searchVector),
])
```

### FTS query using stored vector (Drizzle raw SQL)

```typescript
// Source: adapted from existing search.get.ts + stored column pattern
const rows = await db.execute(sql`
  SELECT
    i.id,
    ts_rank(i.search_vector, websearch_to_tsquery('french', ${q})) AS rank,
    ts_headline('french', i.content, websearch_to_tsquery('french', ${q}),
      'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, MaxFragments=2'
    ) AS highlight
  FROM interventions i
  WHERE i.search_vector @@ websearch_to_tsquery('french', ${q})
  ORDER BY rank DESC
  LIMIT ${limit} OFFSET ${offset}
`)
```

### TypeScript type inference from Drizzle schema

```typescript
// Source: https://orm.drizzle.team/docs/column-types/pg (InferSelectModel)
import type { InferSelectModel, InferInsertModel } from 'drizzle-orm'
import { actors, interventions, crossReferences } from 'shared/schema'

export type Actor = InferSelectModel<typeof actors>
export type NewActor = InferInsertModel<typeof actors>
export type Intervention = InferSelectModel<typeof interventions>
export type CrossReference = InferSelectModel<typeof crossReferences>
```

### Migration workflow commands

```bash
# In packages/shared:

# Step 1: Generate custom rename migration (creates empty SQL file)
pnpm drizzle-kit generate --custom --name=rename-deputies-to-actors

# Step 2: Write the SQL manually in the generated file (see Pattern 2)

# Step 3: Apply the rename migration
pnpm db:migrate

# Step 4: Generate additive migrations for new tables
pnpm drizzle-kit generate --name=add-universal-schema

# Step 5: Apply
pnpm db:migrate

# Step 6: Verify
pnpm db:studio   # Drizzle Studio to visually inspect schema
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|----------------------|
| Functional GIN index `USING gin (to_tsvector(...))` | Stored generated column + GIN index | Replace existing FTS index on actors + interventions |
| Manual trigger for tsvector update | `GENERATED ALWAYS AS ... STORED` (PostgreSQL 12+) | No triggers needed |
| Deputies-only actors table | Polymorphic `actors` table with `actor_type` column | SCHEMA-01 coverage |
| No cross-reference table | `cross_references` with `source_type`/`source_id` | SCHEMA-06 coverage |

**Deprecated in this phase:**
- `packages/web/server/db/schema.ts` — delete this file, use shared only
- `idx_interventions_fts` functional index — replace with stored vector index
- `deputy_id` column name — rename to `actor_id`

---

## Migration Order (Critical)

The migration must be executed in this exact order to avoid FK violations:

```
1. Custom migration: ALTER TABLE deputies RENAME TO actors
                     ALTER TABLE interventions RENAME COLUMN deputy_id TO actor_id
                     (FK constraint follows automatically in PG)

2. Additive migration: Add search_vector generated columns to actors and interventions
                       (Can be done in same or separate migration)

3. Additive migration: New tables (organs, legislatures, sessions, scrutins, votes,
                       questions, amendments, cross_references)

4. Optional: DROP INDEX idx_interventions_fts (old functional index, replaced by stored)
```

Note: Adding a stored generated column to an existing table with 618 actors and 2479
interventions is instant in PostgreSQL — the column is computed synchronously during migration,
but for these data volumes it takes milliseconds.

---

## Open Questions

1. **sessions vs. debates table**
   - What we know: Current `debates` table stores CRI sessions (AN hemicycle only)
   - What's unclear: Should `debates` be renamed to `sessions`, or create `sessions` and migrate?
     The phase requirements say SCHEMA-02 covers "seances, interventions (CRI) avec chambre (AN/Senat)"
   - Recommendation: Add a `chamber` column to existing `debates` table (non-breaking) rather than
     renaming. Can rename to `sessions` in a future phase if needed. Less risk than another rename.

2. **actors.legislature vs. mandats table**
   - What we know: Deputies have legislature numbers; a deputy may serve multiple legislatures
   - What's unclear: Does SCHEMA-01 require a mandats (mandate history) table, or is a single
     `legislature` integer on actors sufficient for v2?
   - Recommendation: Single `legislature` integer for now, with `is_active` boolean. Mandats
     table deferred to v3 per prior decisions.

3. **Drizzle-kit snapshot sync after custom migration**
   - What we know: Custom migrations bypass drizzle-kit snapshot diffing
   - What's unclear: Whether `drizzle-kit generate` after the custom rename migration will correctly
     detect the state (actors table present) without generating a second DROP TABLE
   - Recommendation: After applying the custom migration, run `drizzle-kit generate` with the
     updated TypeScript schema. Inspect the generated SQL carefully before applying. If it
     generates DROP TABLE, the snapshot is out of sync and needs manual repair.

---

## Sources

### Primary (HIGH confidence)

- https://orm.drizzle.team/docs/guides/full-text-search-with-generated-columns — Verified exact
  TypeScript pattern for `customType` + `generatedAlwaysAs()` for tsvector
- https://orm.drizzle.team/docs/generated-columns — Confirmed `generatedAlwaysAs()` API,
  PostgreSQL STORED columns only
- https://orm.drizzle.team/docs/kit-custom-migrations — Confirmed `--custom` flag workflow,
  SQL-only (no JS/TS) in current version
- https://www.postgresql.org/docs/current/textsearch-tables.html — Official PG17 docs: `GENERATED
  ALWAYS AS ... STORED` for tsvector is recommended approach, no triggers needed
- Project codebase (packages/shared/src/schema.ts, packages/web/server/*) — Full current state

### Secondary (MEDIUM confidence)

- GitHub issues drizzle-orm #2533, #5177 — Rename detection sometimes fails (treats as drop+create),
  justifies hand-writing rename migrations
- https://orm.drizzle.team/docs/drizzle-kit-generate — Confirmed `--custom --name` flags available

### Tertiary (LOW confidence)

- WebSearch results on drizzle-kit rename behavior — Multiple sources confirm unreliable rename
  detection; flag for validation before executing on production

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — drizzle-orm 0.45.1 already installed, customType/generatedAlwaysAs
  verified against official Drizzle docs
- Architecture: HIGH — PostgreSQL 17 stored generated column verified against official PG docs,
  migration order derived from FK analysis of existing schema
- Pitfalls: HIGH — Most pitfalls derived from direct code analysis of existing schema + confirmed
  by GitHub issues on drizzle-kit rename behavior

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (drizzle-kit moves fast; re-verify if using a newer version)
