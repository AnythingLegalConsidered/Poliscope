# Architecture Research

**Domain:** Universal parliamentary database integration — Nuxt 4 fullstack monorepo
**Researched:** 2026-03-28
**Confidence:** HIGH (existing codebase read directly; external sources verified)

---

## Current State (Milestone 1 Baseline)

```
Poliscope/ (flat app)
├── app/                    # Nuxt frontend (pages, components, composables)
├── server/
│   ├── api/                # 6 H3 event handlers (debates, deputies, search, sitemap)
│   ├── db/schema.ts        # 5 Drizzle tables
│   └── utils/db.ts         # postgres singleton via useRuntimeConfig()
├── scripts/                # Python ingestion (ingest_deputies.py, ingest_debates.py, tag_interventions.py)
├── shared/                 # Types already extracted here
├── docker-compose.yml      # PostgreSQL 17 + app
└── drizzle.config.ts       # Single schema file
```

**What works well and must be preserved:**
- `db.ts` pattern: single `postgres()` client, `drizzle(client, { schema })`
- `getPaginationParams` + `paginatedResponse` utilities in `server/utils/`
- `routeRules` cache in `nuxt.config.ts` (300s for debates, 3600s for deputies)
- FTS with `to_tsvector('french')` + `websearch_to_tsquery` — keep French config
- `window function count(*) over()` pattern for total counts without extra query

---

## Target Architecture (Milestone 2)

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         MONOREPO ROOT                             │
│                   pnpm-workspace.yaml                             │
├──────────────────────┬───────────────────────────────────────────┤
│   packages/shared    │   packages/web         packages/ingestion  │
│   (TypeScript types  │   (Nuxt 4 app)         (Python scripts)    │
│   + Zod schemas)     │                                            │
├──────────────────────┴────────────────┬───────────────────────────┤
│              packages/api             │                            │
│   (H3 standalone server OR            │    LXC PVE02              │
│    Nuxt server/ kept in web)          │    PostgreSQL 17           │
│                                       │    (single DB, ~15 tables) │
└───────────────────────────────────────┴───────────────────────────┘
```

### Monorepo Structure Recommendation

**Use pnpm workspaces with Nuxt Layers, not a separate Express/H3 server.**

Rationale: The current `server/` code is already tightly coupled to Nuxt's `useRuntimeConfig()` and auto-imports (`defineEventHandler`, `createError`, `getQuery`). Extracting it to a standalone H3 server would require re-wiring all of that plumbing. For a solo dev, the overhead exceeds the benefit. Keep the server inside the Nuxt app; move shared types and ingestion to sibling packages.

```
poliscope/                          # monorepo root
├── pnpm-workspace.yaml
├── package.json                    # root scripts only
├── packages/
│   ├── shared/                     # NEW — TypeScript types + Zod validation
│   │   ├── package.json            # name: "@poliscope/shared"
│   │   ├── src/
│   │   │   ├── types/
│   │   │   │   ├── actors.ts       # Deputy, Senator, Minister interfaces
│   │   │   │   ├── debates.ts      # Debate, Intervention, Session
│   │   │   │   ├── legislative.ts  # Amendment, Vote, Dossier
│   │   │   │   └── api.ts          # PaginatedResponse<T>, ApiError
│   │   │   └── index.ts
│   │   └── tsconfig.json
│   │
│   ├── web/                        # MOVED — current Nuxt app (renamed from root)
│   │   ├── app/                    # frontend pages, components, composables
│   │   ├── server/                 # H3 handlers + Drizzle schema (stays here)
│   │   │   ├── api/
│   │   │   │   ├── actors/         # NEW: deputies, senators, ministers unified
│   │   │   │   ├── debates/        # EXTENDED
│   │   │   │   ├── questions/      # NEW
│   │   │   │   ├── amendments/     # NEW
│   │   │   │   ├── votes/          # NEW
│   │   │   │   ├── dossiers/       # NEW
│   │   │   │   └── search.get.ts   # EXTENDED (cross-type FTS)
│   │   │   ├── db/
│   │   │   │   ├── schema/         # SPLIT — one file per domain
│   │   │   │   │   ├── actors.ts
│   │   │   │   │   ├── debates.ts
│   │   │   │   │   ├── legislative.ts
│   │   │   │   │   └── index.ts    # re-exports all
│   │   │   │   └── schema.ts       # kept as alias for drizzle.config.ts
│   │   │   └── utils/
│   │   │       ├── db.ts
│   │   │       ├── pagination.ts
│   │   │       └── filters.ts      # NEW: shared filter builders
│   │   ├── shared/                 # symlink or re-export from @poliscope/shared
│   │   ├── nuxt.config.ts
│   │   └── package.json            # name: "@poliscope/web", deps on @poliscope/shared
│   │
│   └── ingestion/                  # MOVED — Python scripts
│       ├── pyproject.toml          # replaces requirements.txt
│       ├── config.py
│       ├── db.py
│       ├── sources/
│       │   ├── an/                 # Assemblée Nationale sources
│       │   │   ├── tricoteuses.py  # JSON from git.en-root.org/tricoteuses
│       │   │   ├── dila_cri.py     # MOVED: existing ingest_debates.py
│       │   │   ├── votes.py        # NEW: Scrutins.json.zip from data.assemblee-nationale.fr
│       │   │   ├── amendments.py   # NEW: data.assemblee-nationale.fr XML/JSON
│       │   │   └── questions.py    # NEW: QAG + written questions
│       │   ├── senat/
│       │   │   ├── actors.py       # NEW: senators from nossenateurs.fr JSON
│       │   │   ├── cri.py          # NEW: Senate CR XML
│       │   │   ├── votes.py        # NEW: Scrutins PostgreSQL dump
│       │   │   └── amendments.py   # NEW: Ameli PostgreSQL dump
│       │   └── common/
│       │       ├── name_normalize.py  # MOVED: from ingest_debates.py
│       │       └── upsert.py          # MOVED: from db.py
│       ├── orchestrator.py         # MOVED+EXTENDED: run_all.py
│       └── tag_interventions.py    # MOVED
├── drizzle.config.ts               # at root, points to packages/web/server/db/schema
└── docker-compose.yml
```

---

## Schema Migration Strategy

### Principle: Additive-first, rename-last

The 5 existing tables have live data (2,479 interventions, 618 deputies). The migration path must be zero-data-loss.

**Phase 9 migration order:**

```
Step 1 — Rename tables (breaking, do in single Drizzle migration)
  deputies      → actors          (add: chamber='AN', actor_type='deputy')
  debates       → sessions        (add: chamber column)
  interventions → interventions   (unchanged name, add: session_id alias)
  tags          → tags            (unchanged)
  intervention_tags → intervention_tags  (unchanged)

Step 2 — Add new tables (additive, no risk)
  mandates      (actor_id → organe_id, date_debut, date_fin, role)
  organes       (commissions, groupes politiques, delegations)
  questions     (actor_id, type, content, date, response)
  amendments    (actor_id, session_id, dossier_id, content, sort)
  scrutins      (session_id, type, date, result)
  votes         (scrutin_id, actor_id, position)
  dossiers      (title, legislature, etapes JSON)
  commission_cr (organe_id, session_id, date, content)

Step 3 — Backfill chamber='AN' for existing deputies + sessions data
Step 4 — Add FTS indexes on new text columns (CREATE INDEX CONCURRENTLY)
```

**Generate one Drizzle migration per step, not one mega migration.**
Use `drizzle-kit generate` then inspect SQL before running `drizzle-kit migrate`.

### Critical schema decisions

**actors table (replaces deputies):**
```typescript
export const actors = pgTable('actors', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),  // PA123456 (AN) or SEN-123 (Sénat)
  chamber: text('chamber').notNull(),                  // 'AN' | 'Senat' | 'Gouvernement'
  actorType: text('actor_type').notNull(),             // 'deputy' | 'senator' | 'minister'
  firstName: text('first_name').notNull(),
  lastName: text('last_name').notNull(),
  fullName: text('full_name').notNull(),
  photoUrl: text('photo_url'),
  isActive: boolean('is_active').default(true),
  // Denormalized for query performance (no join needed for common filters)
  currentGroup: text('current_group'),
  currentConstituency: text('current_constituency'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
})
```

**Why denormalize group into actors:** Every list query filters/groups by political group. A join to mandates on every `/api/actors` call is expensive. Keep the current value denormalized, sync on ingestion.

**sessions table (replaces debates):**
```typescript
export const sessions = pgTable('sessions', {
  // ...existing debate columns...
  chamber: text('chamber').notNull().default('AN'),  // 'AN' | 'Senat' | 'Commission'
  sessionCategory: text('session_category'),          // 'hemicycle' | 'commission' | 'QAG'
})
```

---

## API Layer Redesign

### Existing endpoints — what changes

| Current Endpoint | Milestone 2 Change | Impact |
|-----------------|-------------------|--------|
| `GET /api/debates` | Add `?chamber=` filter | Non-breaking — new optional param |
| `GET /api/debates/:id` | Session now has `chamber` field | Non-breaking — additive |
| `GET /api/deputies` | Rename path to `/api/actors` + add `?chamber=` | Breaking — need redirect or alias |
| `GET /api/deputies/:id` | Same rename | Breaking |
| `GET /api/search` | Extend to cross-type FTS | Additive — new optional `?type=` param |
| `GET /api/health` | Keep as-is | No change |

**Recommendation for deputies → actors rename:** Keep `/api/deputies` as an alias (forwarding to `/api/actors?chamber=AN`) during frontend transition. Remove alias in Phase 16. This avoids a flag day requiring simultaneous frontend + API changes.

### New endpoints (Phase 15)

```
GET /api/actors                 # unified list (deputies + senators + ministers)
GET /api/actors/:id             # profile with all mandates, votes, amendments
GET /api/actors/:id/votes       # scrutins by actor, paginated
GET /api/actors/:id/amendments  # amendments by actor, paginated
GET /api/questions              # QAG + written + QOSD, filterable
GET /api/questions/:id
GET /api/amendments             # list with filters (sort, author, dossier)
GET /api/amendments/:id
GET /api/votes                  # scrutins list
GET /api/votes/:id              # full vote breakdown by actor
GET /api/dossiers               # legislative dossiers
GET /api/dossiers/:id
GET /api/organes                # commissions, groups
GET /api/organes/:id
GET /api/search                 # extended: type=debate|question|amendment|all
```

**OpenAPI:** Use `@scalar/nuxt` (Scalar's Nuxt integration) to auto-generate docs from JSDoc annotations on event handlers. This is lower overhead than managing a separate Swagger YAML.

### API response pattern — keep existing, extend it

The current `paginatedResponse()` utility and `count(*) over()` window function pattern works well. Extend it, don't replace it. For nested resources (actor's votes, actor's amendments), reuse the same `PaginatedResponse<T>` shape.

---

## Ingestion Pipeline Architecture

### Source map and formats

| Source | Entities | Format | Update Frequency | Confidence |
|--------|----------|--------|-----------------|------------|
| Tricoteuses (git.en-root.org) | AN deputies, ministers, organes | JSON (one file per actor/organe) | Daily git push | HIGH |
| data.assemblee-nationale.fr | Votes (scrutins) | `Scrutins.json.zip` | Daily | HIGH |
| data.assemblee-nationale.fr | Amendments | ZIP archives | Daily | HIGH |
| data.assemblee-nationale.fr | Questions (QAG, ecrites) | XML/JSON bulk | Daily | HIGH |
| DILA CRI | AN debates/interventions | `.taz` (tar of tar of XML) | By parution | HIGH |
| nossenateurs.fr | Senators | JSON API (`/senateurs/json`) | On demand | MEDIUM |
| data.senat.fr | Senate votes (Dosleg) | PostgreSQL SQL dump | Daily | HIGH |
| data.senat.fr | Senate amendments (Ameli) | PostgreSQL SQL dump | Daily | HIGH |
| data.senat.fr | Senate CRI | XML | Irregular | MEDIUM |

**Note on Tricoteuses migration:** Framagit is closing. New source is `git.en-root.org/tricoteuses/data`. The `@tricoteuses/assemblee` npm package may no longer be maintained. Use direct git clone or HTTP fetch of the JSON files instead.

**Note on Senate SQL dumps:** data.senat.fr provides full PostgreSQL 8.4-format SQL dumps for amendments and votes. These must be loaded into a throwaway local DB, then extracted via `pg_dump --data-only` or Python psycopg2 queries. Do not pipe these directly into the production DB.

### Ingestion pipeline design

```
External Sources
      │
      ▼
┌─────────────────────────────────────────┐
│           packages/ingestion/           │
│                                         │
│  sources/an/tricoteuses.py              │ ─── git clone → parse JSON → actors
│  sources/an/dila_cri.py                 │ ─── HTTP .taz → parse XML → sessions+interventions
│  sources/an/votes.py                    │ ─── HTTP zip → parse JSON → scrutins+votes
│  sources/an/amendments.py              │ ─── HTTP zip → parse XML/JSON → amendments
│  sources/an/questions.py               │ ─── HTTP bulk → parse XML → questions
│  sources/senat/actors.py               │ ─── HTTP JSON → parse → actors
│  sources/senat/votes.py                │ ─── SQL dump → import staging → extract
│  sources/senat/amendments.py           │ ─── SQL dump → import staging → extract
│  sources/senat/cri.py                  │ ─── HTTP XML → parse → sessions+interventions
│                                         │
│  orchestrator.py                        │ ─── sequences above, handles deps
│  tag_interventions.py                   │ ─── runs AFTER CRI ingestion
└─────────────────────────────────────────┘
      │
      ▼
┌──────────────────────┐
│  PostgreSQL 17 (LXC) │
│  Single database     │
│  ~15 tables          │
└──────────────────────┘
```

**Ingestion dependency order (critical):**
```
1. actors (AN + Sénat) — must exist before anything references actor_id
2. organes — must exist before mandates
3. mandates — joins actors to organes
4. sessions (debates) — independent
5. interventions — requires actors + sessions
6. questions — requires actors
7. amendments — requires actors + dossiers
8. dossiers — independent
9. scrutins — requires sessions
10. votes — requires scrutins + actors
11. commission_cr — requires organes + sessions
12. tag_interventions — requires interventions
```

**Idempotence contract:** Every script must be re-runnable safely. Pattern: upsert on `official_id` (for actors), or delete-then-insert for ordered sets (interventions per session). Existing `db.py:upsert_query()` handles this — extend it, don't replace it.

---

## Component Boundaries

| Component | Owns | Does NOT own | Interface |
|-----------|------|-------------|-----------|
| `packages/shared` | TypeScript interfaces, Zod schemas, API response shapes | No runtime logic, no DB | npm package import |
| `packages/web/server/db/schema/` | Drizzle table definitions, indexes | Business logic | Imported by event handlers |
| `packages/web/server/api/` | HTTP handling, query construction, pagination | Data transformation business rules | H3 event handlers |
| `packages/web/app/` | Vue components, composables, pages | No direct DB access | `useFetch('/api/...')` |
| `packages/ingestion/` | Data fetch + parse + DB write | No HTTP API serving | CLI scripts + cron |

---

## Data Flow

### Read path (user request)

```
Browser
  → useFetch('/api/debates?page=2&chamber=AN')
  → Nuxt routeRules cache check (300s TTL)
  → server/api/debates/index.get.ts
  → Drizzle query with .where() conditions
  → PostgreSQL (FTS index for search, B-tree for filters)
  → paginatedResponse() wrapper
  → JSON response
```

### Write path (ingestion)

```
Cron (weekly / on-demand)
  → orchestrator.py
  → source-specific fetcher (HTTP / git clone / SQL dump)
  → parser (XML / JSON)
  → name_normalize.py (actor matching)
  → db.py upsert_query() with psycopg2
  → PostgreSQL UPSERT ON CONFLICT (official_id)
  → tag_interventions.py (keyword scan on new interventions)
```

### Cross-type FTS (new in Phase 15)

```
GET /api/search?q=immigration&type=all
  → Build UNION query across:
     - interventions (to_tsvector('french', content))
     - questions (to_tsvector('french', content || ' ' || title))
     - amendments (to_tsvector('french', expose_motifs || ' ' || content))
  → Add result_type column to distinguish in response
  → ts_rank + ts_headline on matched content
  → Single paginatedResponse, mixed types
```

**Warning:** Cross-type UNION FTS queries will be slower than single-table FTS. Index each table separately, not a combined index. Let PostgreSQL plan per-table and UNION the results. Test with EXPLAIN ANALYZE before deploying.

---

## Architectural Patterns

### Pattern 1: Schema by domain (not by layer)

**What:** Split `server/db/schema.ts` into `schema/actors.ts`, `schema/debates.ts`, `schema/legislative.ts`.
**When to use:** Once you exceed 8-10 tables in a single file.
**Trade-offs:** Circular imports are possible if tables reference each other across files. Solution: define FK references lazily (arrow functions) in Drizzle, which it already supports.

```typescript
// schema/debates.ts
import { actors } from './actors'
export const interventions = pgTable('interventions', {
  actorId: integer('actor_id').references(() => actors.id),  // lazy reference
  // ...
})
```

### Pattern 2: Denormalized current state + normalized history

**What:** Store the actor's current political group directly on the `actors` row, but maintain a full `mandates` table for history.
**When to use:** Any attribute that is filtered frequently in list queries.
**Trade-offs:** Ingestion must update both the denormalized field and the mandates table. Worth it — joining mandates for every deputy list query at scale is a known bottleneck.

### Pattern 3: Staging table for SQL dump imports (Senate)

**What:** Import Senate SQL dumps (Ameli amendments, Dosleg votes) into a temporary local PostgreSQL instance, extract relevant rows, then insert into production schema.
**When to use:** When the source schema is incompatible with your schema and requires transformation.
**Example:**
```bash
# Spin up throwaway container
docker run -d --name senat-staging postgres:17
docker cp ameli_dump.sql senat-staging:/tmp/
docker exec senat-staging psql -U postgres -f /tmp/ameli_dump.sql
# Then Python connects to staging + production and migrates
```

### Pattern 4: Chamber-agnostic API with optional filter

**What:** Single `/api/actors` endpoint returns all chambers, `?chamber=AN` filters.
**When to use:** All actor-type endpoints.
**Trade-offs:** Frontend must always pass `?chamber=AN` on pages that only show deputies — this is explicit and correct. Avoids maintaining separate URL spaces per chamber.

---

## Anti-Patterns

### Anti-Pattern 1: Separate standalone H3 server package

**What people do:** Create `packages/api/` as a standalone `h3` server to separate API from frontend.
**Why it's wrong for this project:** Nuxt's auto-imports (`defineEventHandler`, `createError`, `getPaginationParams`, `db`) would all need to be manually re-imported. `useRuntimeConfig()` is a Nuxt-specific API. The migration cost is high, the benefit (API usable without Nuxt) is zero — there is no other client.
**Do this instead:** Keep `server/` inside the Nuxt app. Only extract truly shared _types_ to `packages/shared`.

### Anti-Pattern 2: One mega Drizzle migration file

**What people do:** Generate a single migration that renames deputies→actors, adds 10 new tables, and alters 3 columns.
**Why it's wrong:** If the migration fails mid-way on production, rollback is manual and painful. Drizzle's `drizzle-kit migrate` runs SQL files sequentially — if step 3 of 15 fails, you have a half-migrated schema.
**Do this instead:** One migration file per intent. `001_rename_deputies_to_actors.sql`, `002_add_actors_chamber_column.sql`, etc. Each file must be independently safe to apply and rollback.

### Anti-Pattern 3: FTS on joined data at query time

**What people do:** Build cross-type search by doing `SELECT * FROM interventions i JOIN actors a ... WHERE to_tsvector(i.content || a.full_name) @@ query`.
**Why it's wrong:** The GIN index on `to_tsvector()` is per-column. Joining before vectorizing bypasses the index entirely — full sequential scan.
**Do this instead:** Index each column separately, filter at the index level, join after. Or use a materialized search index table updated by trigger.

### Anti-Pattern 4: Ingesting Senate SQL dumps directly into production DB

**What people do:** `psql production_db < ameli_dump.sql` to restore Senate amendment data.
**Why it's wrong:** The Senate dump uses its own schema names, table structures, and potentially PostgreSQL extensions incompatible with your schema. It will overwrite tables or fail with constraint errors.
**Do this instead:** Use a staging container (see Pattern 3). Extract only the rows you need via SELECT, transform to your schema, INSERT into production.

---

## Integration Points

### New vs. Modified — explicit list

**Modified (existing code changes required):**

| File | Change | Risk |
|------|--------|------|
| `server/db/schema.ts` | Split into `schema/` folder, rename deputies→actors, add chamber | HIGH — affects all imports |
| `server/api/deputies/index.get.ts` | Point to actors table, add ?chamber filter | MEDIUM |
| `server/api/deputies/[id].get.ts` | Point to actors table | MEDIUM |
| `server/api/debates/index.get.ts` | Add ?chamber filter | LOW |
| `server/api/search.get.ts` | Extend for cross-type, add ?type param | MEDIUM |
| `server/utils/db.ts` | Update schema import path | LOW |
| `scripts/ingest_deputies.py` | Rename/move to `sources/an/tricoteuses.py`, update table name | MEDIUM |
| `scripts/ingest_debates.py` | Move to `sources/an/dila_cri.py`, update actor_id ref | MEDIUM |

**New (no existing code touched):**

| File | Purpose |
|------|---------|
| `packages/shared/src/types/` | All shared TypeScript interfaces |
| `pnpm-workspace.yaml` | Monorepo root |
| `packages/web/server/db/schema/actors.ts` | actors + mandates + organes |
| `packages/web/server/db/schema/legislative.ts` | questions + amendments + scrutins + votes + dossiers |
| `packages/web/server/api/questions/` | Questions endpoints |
| `packages/web/server/api/amendments/` | Amendments endpoints |
| `packages/web/server/api/votes/` | Scrutins + vote breakdown endpoints |
| `packages/web/server/api/dossiers/` | Legislative dossiers endpoints |
| `packages/web/server/api/organes/` | Commissions + groups endpoints |
| `packages/ingestion/sources/an/votes.py` | Scrutins.json.zip ingestion |
| `packages/ingestion/sources/an/amendments.py` | AN amendments ingestion |
| `packages/ingestion/sources/an/questions.py` | QAG + written questions ingestion |
| `packages/ingestion/sources/senat/` | All Senate sources |
| `packages/ingestion/common/staging.py` | Senate SQL dump staging helper |

### Build order for phases (dependency-aware)

```
Phase 8: Monorepo restructure
  └── pnpm-workspace.yaml + move files (no logic changes)
  └── Validate: existing endpoints still work after move

Phase 9: Schema migration
  └── Requires: Phase 8 complete (monorepo structure in place)
  └── Step 1: Rename tables (breaking — coordinate with frontend in same PR)
  └── Step 2-3: Add tables (safe, additive)
  └── Step 4: Backfill + FTS indexes CONCURRENTLY

Phase 10: Actors + Organes ingestion
  └── Requires: Phase 9 (new tables exist)
  └── Tricoteuses source first (AN deputies — can diff against existing 618)
  └── nossenateurs.fr second (senators)
  └── Ministres last (simplest format)

Phase 11: CRI debates ingestion (AN + Sénat)
  └── Requires: Phase 10 (actor_id FKs must resolve)
  └── AN DILA CRI first (existing code refactored)
  └── Senate CRI second (new parser)

Phase 12: Questions ingestion
  └── Requires: Phase 10 (actor_id)
  └── No dependency on Phase 11 (debates)

Phase 13: Amendments + Votes ingestion
  └── Requires: Phase 10 (actors), Phase 11 (sessions for scrutin → session_id)
  └── Amendments: data.assemblee-nationale.fr zip + Senate Ameli dump (staging)
  └── Votes: data.assemblee-nationale.fr Scrutins.json.zip + Senate Dosleg dump

Phase 14: Dossiers + Commission CR
  └── Requires: Phase 11 (sessions), Phase 13 (amendments reference dossiers)
  └── Can run in parallel with Phase 13 if dossier table added in Phase 9

Phase 15: API REST universelle
  └── Requires: Phase 9-14 complete (all tables populated)
  └── Modify existing endpoints first (add chamber filter, actor rename)
  └── Add new endpoints in dependency order: organes → actors → debates → questions → amendments → votes → dossiers
  └── OpenAPI docs last (after endpoints stable)

Phase 16: Frontend adaptation
  └── Requires: Phase 15 (all API endpoints available)
  └── Update existing composables (deputies → actors API path)
  └── New pages in order: senators → votes → amendments → dossiers

Phase 17: Deploy + Ops
  └── Requires: Phase 16 complete
  └── PostgreSQL 17 on LXC first
  └── Migrate data to LXC
  └── Deploy Nuxt app pointing to LXC DB
  └── Cron for weekly ingestion refresh
```

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (single user, dev) | Current Nuxt + Docker is fine |
| Public launch (~1k users) | Add `routeRules` cache to all new endpoints; existing cache pattern works |
| 10k users | PostgreSQL connection pooling (pgBouncer in front of PostgreSQL) — the `postgres()` singleton becomes a bottleneck under concurrent load |
| 100k+ users | Read replicas for SELECT-heavy endpoints (search, actor profiles); separate write path for ingestion |

**First bottleneck at scale:** The `server/utils/db.ts` creates a single `postgres()` client that opens a persistent connection pool. Under Nuxt's Node.js server with multiple concurrent requests, this is fine up to ~50 concurrent requests. Beyond that, consider `postgres({ max: 20 })` explicit pool config.

**Second bottleneck:** Cross-type FTS UNION queries at Phase 15. Each UNION branch hits a GIN index — but UNION itself is not parallelized by PostgreSQL by default. At high volume, a dedicated search table (materialized view updated by trigger) is the fix.

---

## Sources

- Existing codebase: `server/db/schema.ts`, `server/api/`, `scripts/` (read directly, HIGH confidence)
- data.assemblee-nationale.fr vote format: [Votes — Opendata AN](https://data.assemblee-nationale.fr/travaux-parlementaires/votes) — XML/JSON `Scrutins.json.zip` (MEDIUM confidence, page confirmed)
- data.senat.fr dataset overview: [Données Sénat](https://data.senat.fr/donnees/) — PostgreSQL dumps for Ameli + Dosleg (MEDIUM confidence)
- data.assemblee-nationale.fr FAQ: [FAQ OpenData](https://data.assemblee-nationale.fr/foire-aux-questions) — confirms formats + bulk download (HIGH confidence)
- Tricoteuses migration from Framagit: [Search results](https://framagit.org/tricoteuses/open-data-assemblee-nationale) — new URL is `git.en-root.org/tricoteuses/data` (MEDIUM confidence — Framagit gave 403)
- pnpm workspace best practices: [Vue School — Scalable Nuxt 3 Monorepos](https://vueschool.io/articles/vuejs-tutorials/scalable-nuxt-3-monorepos-with-pnpm-workspaces/) (HIGH confidence)
- Drizzle migration patterns: [Drizzle ORM Migrations docs](https://orm.drizzle.team/docs/migrations) (HIGH confidence)

---

*Architecture research for: Poliscope — Universal Parliamentary Database integration*
*Researched: 2026-03-28*
