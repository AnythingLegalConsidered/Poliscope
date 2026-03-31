# Phase 13: API REST Universelle + OpenAPI - Research

**Researched:** 2026-03-31
**Domain:** Nuxt 3 server API extension + OpenAPI documentation (Nitro + @scalar/nuxt)
**Confidence:** HIGH

## Summary

Phase 13 extends the existing Nuxt 3/Nitro API to cover the new data (scrutins/votes from Phase 12) and adds an OpenAPI documentation UI. The existing codebase already has a working pattern: Drizzle ORM queries in `defineEventHandler`, paginated via shared `getPaginationParams`/`paginatedResponse` utils, with `chamber` filter already implemented in `/api/debates`. The new endpoints follow that exact pattern.

The OpenAPI documentation is handled natively by Nitro's experimental `openAPI` feature (no third-party schema generator needed) combined with `@scalar/nuxt` module for the UI. Each route adds a `defineRouteMeta({ openAPI: {...} })` block above the handler — that is the only addition needed to document any endpoint. The Scalar UI is exposed at `/_scalar` (or a custom path) and can optionally be proxied to `/api/docs`.

The FTS cross-type search (API-05) is the highest-complexity task. The existing `search.get.ts` queries a single table (interventions). Extending it to also return scrutins requires a UNION approach: two sub-queries with a shared `type` discriminant column, each using their respective stored `search_vector` (interventions has one; scrutins does not have a `search_vector` yet — this needs adding). The recommended approach is a raw SQL UNION with `db.execute(sql\`...\`)` matching the existing pattern.

**Primary recommendation:** Reuse existing Drizzle + pagination patterns for all new endpoints; use Nitro's built-in `openAPI` feature + `@scalar/nuxt` for docs — no custom schema tooling needed.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@scalar/nuxt` | 0.6.18 (latest) | Scalar API Reference UI module for Nuxt | Official Nuxt module, renders docs from Nitro's generated OpenAPI spec |
| Nitro `experimental.openAPI` | Built-in (Nuxt 4.4.2) | Auto-generates OpenAPI JSON from `defineRouteMeta` annotations | No extra package, zero overhead |
| `drizzle-orm` | 0.45.1 (already in project) | DB queries for new scrutins/votes endpoints | Already used, consistent with existing API routes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `h3` (built-in) | Built-in Nitro | `sendRedirect` for backward-compat route aliases | If `/api/actors` alias for `/api/deputies` is needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Nitro `experimental.openAPI` | `swagger-jsdoc` or `zod-to-openapi` | Extra deps, manual wiring — Nitro's built-in is simpler for this project |
| `@scalar/nuxt` | `swagger-ui-express` or raw Swagger HTML | Not Nuxt-native; Scalar has better UX and is actively maintained |
| Raw SQL UNION for cross-type FTS | Separate endpoints then merge in handler | UNION is one DB round-trip, better rank merging |

**Installation (new packages only):**
```bash
cd packages/web
pnpm add @scalar/nuxt
```

---

## Architecture Patterns

### Recommended Project Structure
```
packages/web/server/api/
├── votes/
│   ├── index.get.ts       # GET /api/votes — list scrutins with filters
│   └── [id].get.ts        # GET /api/votes/:id — scrutin detail + per-actor positions
├── actors/                # NEW: alias folder (optional backward compat)
│   └── index.get.ts       # 301 redirect → /api/deputies
├── debates/               # EXISTING — add chambre filter + defineRouteMeta
│   ├── index.get.ts
│   └── [id].get.ts
├── deputies/              # EXISTING — add chambre filter + defineRouteMeta
│   ├── index.get.ts
│   └── [id].get.ts
├── search.get.ts          # EXISTING — extend to cross-type (debates + votes)
└── health.get.ts          # EXISTING — add defineRouteMeta
```

### Pattern 1: Route Metadata for OpenAPI (defineRouteMeta)
**What:** Annotate each server route with OpenAPI metadata above the handler.
**When to use:** All API routes in this phase.
**Example:**
```typescript
// Source: nitro.build/config + mokkapps.de/blog/document-your-nuxt-endpoints-with-open-api-and-visualize-with-swagger-or-scalar
defineRouteMeta({
  openAPI: {
    tags: ['votes'],
    summary: 'Liste des scrutins',
    description: 'Retourne la liste paginée des scrutins avec filtres optionnels.',
    parameters: [
      { in: 'query', name: 'chambre', required: false, schema: { type: 'string', enum: ['AN', 'Senat'] } },
      { in: 'query', name: 'page',    required: false, schema: { type: 'integer', default: 1 } },
      { in: 'query', name: 'limit',   required: false, schema: { type: 'integer', default: 20 } },
    ],
    responses: {
      200: {
        description: 'Liste paginée des scrutins',
        content: {
          'application/json': {
            schema: {
              type: 'object',
              properties: {
                data: { type: 'array', items: { $ref: '#/components/schemas/Scrutin' } },
                pagination: { $ref: '#/components/schemas/Pagination' },
              },
            },
          },
        },
      },
    },
  },
})
export default defineEventHandler(async (event) => { ... })
```

### Pattern 2: New scrutins/votes endpoints
**What:** Follow exactly the same pattern as existing `debates/index.get.ts`.
**When to use:** `GET /api/votes` and `GET /api/votes/:id`.
**Example (GET /api/votes):**
```typescript
// Mirrors debates/index.get.ts pattern
import { sql, desc, eq, and, gte, lte } from 'drizzle-orm'
import type { SQL } from 'drizzle-orm'
import { scrutins } from 'shared/schema'

export default defineEventHandler(async (event) => {
  const { page, limit, offset } = getPaginationParams(event)
  const query = getQuery(event)
  const chamber = query.chamber as string | undefined
  const groupe = query.groupe as string | undefined

  const conditions: SQL[] = []
  if (chamber === 'AN' || chamber === 'Senat') {
    conditions.push(eq(scrutins.chamber, chamber))
  }

  const rows = await db
    .select({
      id: scrutins.id,
      officialId: scrutins.officialId,
      title: scrutins.title,
      date: scrutins.date,
      chamber: scrutins.chamber,
      scrutinType: scrutins.scrutinType,
      result: scrutins.result,
      votesFor: scrutins.votesFor,
      votesAgainst: scrutins.votesAgainst,
      votesAbstain: scrutins.votesAbstain,
      sourceUrl: scrutins.sourceUrl,
      totalCount: sql<number>`count(*) over()`,
    })
    .from(scrutins)
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .orderBy(desc(scrutins.date))
    .limit(limit)
    .offset(offset)

  const total = Number(rows.at(0)?.totalCount ?? 0)
  const data = rows.map(({ totalCount, ...rest }) => rest)
  return paginatedResponse(data, total, page, limit)
})
```

### Pattern 3: GET /api/votes/:id (scrutin detail + per-actor positions)
**What:** Return scrutin metadata + paginated list of individual actor votes (joined with actors table).
**When to use:** Detail page, actor-level position visibility.
**Example:**
```typescript
// GET /api/votes/[id].get.ts
import { eq, sql } from 'drizzle-orm'
import { scrutins, votes, actors } from 'shared/schema'

// Fetch scrutin
const scrutinRows = await db.select().from(scrutins).where(eq(scrutins.id, id)).limit(1)
if (!scrutinRows.length) throw createError({ statusCode: 404, message: 'Scrutin not found' })

// Fetch per-actor votes with pagination (1308512 votes total — pagination is MANDATORY)
const voteRows = await db
  .select({
    actorId: votes.actorId,
    position: votes.position,
    actorFullName: actors.fullName,
    actorGroup: actors.group,
    totalCount: sql<number>`count(*) over()`,
  })
  .from(votes)
  .leftJoin(actors, eq(votes.actorId, actors.id))
  .where(eq(votes.scrutinId, id))
  .limit(limit)
  .offset(offset)
```

### Pattern 4: FTS cross-type UNION
**What:** Extend `search.get.ts` to return both interventions AND scrutins in one response.
**When to use:** GET /api/search?q=... — cross-type results.
**Critical prerequisite:** `scrutins` table has no `search_vector` column yet. It must be added via Drizzle migration before this query works efficiently.
**Example SQL pattern:**
```typescript
// Raw SQL UNION approach — matches existing search.get.ts style
const rows = await db.execute(sql`
  SELECT
    'intervention' AS type,
    i.id,
    ts_rank(i.search_vector, websearch_to_tsquery('french', ${q})) AS rank,
    ts_headline('french', i.content, websearch_to_tsquery('french', ${q}),
      'MaxWords=35, MinWords=15, MaxFragments=2') AS highlight,
    d.title AS context_title,
    d.date  AS context_date,
    NULL    AS result,
    count(*) OVER() AS total_count
  FROM interventions i
  LEFT JOIN debates d ON i.debate_id = d.id
  WHERE i.search_vector @@ websearch_to_tsquery('french', ${q})

  UNION ALL

  SELECT
    'scrutin' AS type,
    s.id,
    ts_rank(to_tsvector('french', s.title), websearch_to_tsquery('french', ${q})) AS rank,
    ts_headline('french', s.title, websearch_to_tsquery('french', ${q}),
      'MaxWords=35, MinWords=15, MaxFragments=1') AS highlight,
    s.title AS context_title,
    s.date  AS context_date,
    s.result AS result,
    count(*) OVER() AS total_count
  FROM scrutins s
  WHERE to_tsvector('french', s.title) @@ websearch_to_tsquery('french', ${q})

  ORDER BY rank DESC
  LIMIT ${limit} OFFSET ${offset}
`)
```

### Pattern 5: Nuxt config for OpenAPI + Scalar
**What:** Enable Nitro's openAPI experimental feature + add @scalar/nuxt module.
**When to use:** `nuxt.config.ts` update.
```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  modules: ['@scalar/nuxt'],           // ADD
  nitro: {
    experimental: {
      openAPI: true,                   // ADD
    },
    openAPI: {
      production: 'runtime',           // ADD — enables docs in production
      meta: {
        title: 'Poliscope API',
        description: 'API publique Poliscope — débats, scrutins, acteurs',
        version: '1.0.0',
      },
      ui: {
        scalar: {
          route: '/api/docs',          // Custom route instead of /_scalar
        },
      },
    },
  },
  // ... existing config
})
```

### Anti-Patterns to Avoid
- **Not paginating /api/votes/:id votes sub-list:** With 1.3M votes in DB, returning all votes for a scrutin without pagination will OOM the server. Always paginate.
- **Declaring defineRouteMeta inside the handler:** It must be at the module top level (before `export default`), not inside the event handler function.
- **Building a custom OpenAPI JSON endpoint:** Nitro generates `/_openapi.json` automatically from `defineRouteMeta` annotations — don't hand-roll it.
- **Doing FTS UNION without indexes:** Running `to_tsvector()` at query time on the `scrutins.title` column for every row is slow. Either add a stored `search_vector` column or accept slow FTS for scrutins (acceptable for MVP given `scrutins` has only 7062 rows).
- **Forgetting `production: 'runtime'` for Scalar:** By default, `/_scalar` and `/_openapi.json` are disabled in production builds. Explicitly set this or docs won't be accessible after deployment.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAPI spec generation | Manual JSON/YAML spec file | Nitro `defineRouteMeta` + `experimental.openAPI` | Auto-syncs with code, zero maintenance |
| Swagger/Scalar UI serving | Custom Vue page with embedded viewer | `@scalar/nuxt` module | Handles routing, theming, production config |
| Cross-type search merge | Application-level merge of two separate API calls | UNION SQL query | One DB round-trip, correct rank ordering |
| Chamber filter | Custom middleware | Inline `eq(table.chamber, chamber)` condition | Already done this way in debates endpoint |

**Key insight:** Nitro already does the hard work — route scanning, `defineRouteMeta` extraction, and JSON generation. Adding `@scalar/nuxt` is literally 2 lines in nuxt.config.ts to get a fully functional docs UI.

---

## Common Pitfalls

### Pitfall 1: Votes endpoint N+1 without pagination
**What goes wrong:** `/api/votes/:id` joins `votes` + `actors` — 7062 scrutins × ~185 votes average = 1.3M rows. Returning all votes for a popular scrutin in one response = memory crash.
**Why it happens:** Developer models it like the existing `/api/debates/:id` which returns all interventions (typically < 100).
**How to avoid:** Always apply `limit`/`offset` via `getPaginationParams` on the votes sub-query. Return a `paginatedResponse` for the votes list.
**Warning signs:** Handler takes > 5s on large scrutins, memory spike in Node.

### Pitfall 2: OpenAPI routes disabled in production
**What goes wrong:** Scalar UI works locally at `/_scalar` but returns 404 in production.
**Why it happens:** Nitro disables `openAPI` routes in production by default.
**How to avoid:** Set `nitro.openAPI.production: 'runtime'` in nuxt.config.ts.
**Warning signs:** 404 on `/_scalar` or `/api/docs` after deploy.

### Pitfall 3: defineRouteMeta not picked up by Nitro
**What goes wrong:** `defineRouteMeta(...)` call exists but endpoint doesn't appear in Scalar UI.
**Why it happens:** The call is inside the event handler function, or the syntax is wrong.
**How to avoid:** Place `defineRouteMeta({ openAPI: {...} })` at the TOP of the file, before `export default defineEventHandler(...)`, as a bare statement (not inside a function).
**Warning signs:** Endpoint missing from `/_openapi.json`.

### Pitfall 4: Cross-type UNION total_count wrong
**What goes wrong:** `count(*) OVER()` in UNION gives count per sub-query, not total UNION count.
**Why it happens:** Window functions run before UNION merging.
**How to avoid:** Wrap the UNION in a subquery and apply the window function outside:
```sql
SELECT *, count(*) OVER() AS total_count FROM (
  SELECT ... FROM interventions WHERE ...
  UNION ALL
  SELECT ... FROM scrutins WHERE ...
) sub
ORDER BY rank DESC
LIMIT $limit OFFSET $offset
```
**Warning signs:** `total_count` returns wrong value (e.g., interventions count only).

### Pitfall 5: scrutins.title FTS without stored search_vector
**What goes wrong:** Cross-type search runs `to_tsvector('french', s.title)` at query time — not indexed, full table scan.
**Why it happens:** `scrutins` table currently has no `search_vector` generated column (unlike `interventions`).
**How to avoid:** For 7062 scrutins, the full-scan is acceptable (< 50ms). But if adding a stored column is desired, it requires a Drizzle schema migration + `drizzle-kit push`. Since this is an API phase (not schema migration phase), use the at-query-time approach for now unless performance testing shows a problem.
**Warning signs:** Search queries > 500ms when filtering only scrutins.

---

## Code Examples

Verified patterns from official sources:

### Enabling OpenAPI in nuxt.config.ts
```typescript
// Source: nitro.build/config + nuxt.com/modules/scalar
export default defineNuxtConfig({
  modules: ['@scalar/nuxt'],
  nitro: {
    experimental: { openAPI: true },
    openAPI: {
      production: 'runtime',
      meta: { title: 'Poliscope API', version: '1.0.0' },
      ui: { scalar: { route: '/api/docs' } },
    },
  },
})
```

### Full defineRouteMeta pattern for paginated list endpoint
```typescript
// Source: mokkapps.de blog + nitro.build/config docs
defineRouteMeta({
  openAPI: {
    tags: ['scrutins'],
    summary: 'Liste des scrutins',
    parameters: [
      { in: 'query', name: 'chamber', schema: { type: 'string', enum: ['AN', 'Senat'] } },
      { in: 'query', name: 'page',    schema: { type: 'integer', default: 1 } },
      { in: 'query', name: 'limit',   schema: { type: 'integer', default: 20, maximum: 100 } },
    ],
    responses: {
      200: { description: 'OK', content: { 'application/json': { schema: { type: 'object' } } } },
      500: { description: 'Internal server error' },
    },
  },
})
export default defineEventHandler(async (event) => { ... })
```

### Backward-compatible alias for /api/actors → /api/deputies
```typescript
// server/api/actors/index.get.ts
// Source: H3 sendRedirect — nuxt.com/docs/directory-structure/server
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const qs = new URLSearchParams(query as Record<string, string>).toString()
  return sendRedirect(event, `/api/deputies${qs ? '?' + qs : ''}`, 301)
})
```

### Adding chamber filter to existing actors/deputies endpoint
```typescript
// Modify packages/web/server/api/deputies/index.get.ts
// Currently filters by group and search — add chamber:
const chamber = query.chamber as string | undefined
if (chamber === 'AN' || chamber === 'Senat') {
  conditions.push(eq(actors.chamber, chamber))
}
// actors.chamber column exists in schema (added in Phase 10)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual OpenAPI YAML files | `defineRouteMeta` + Nitro auto-generation | Nitro 2.x (2024) | No spec drift — docs auto-sync with code |
| Swagger UI as separate service | `@scalar/nuxt` module | 2024 | Integrated into Nuxt app, one deploy |
| `/api/deputies` (deputies only) | `/api/actors` covering AN + Sénat | Phase 10 schema | `actors.actorType` + `actors.chamber` distinguish them |

**Deprecated/outdated:**
- Separate `swagger-jsdoc` package: Not needed — Nitro handles spec generation natively when `experimental.openAPI: true`.
- `nuxt-openapi-docs-module`: Older community module, less maintained than `@scalar/nuxt`.

---

## Open Questions

1. **Should `/api/docs` redirect to `/_scalar` or should Scalar serve at `/api/docs` directly?**
   - What we know: `@scalar/nuxt` supports a custom `ui.scalar.route` in Nitro config — can set to `/api/docs`.
   - What's unclear: Whether setting `route: '/api/docs'` in `nitro.openAPI.ui.scalar` works correctly in Nuxt 4 context (no version-specific confirmation found).
   - Recommendation: Default to custom route `/api/docs` via Nitro config. If that doesn't work, use a simple server route that `sendRedirect`s from `/api/docs` to `/_scalar`.

2. **Does `scrutins` need a stored `search_vector` for FTS, or is at-query-time `to_tsvector` acceptable?**
   - What we know: 7062 scrutins. `to_tsvector` at query time on 7062 rows is a full sequential scan — benchmarks suggest ~20-50ms for this size.
   - What's unclear: Whether performance is acceptable without the index. No production load test data available.
   - Recommendation: Use at-query-time `to_tsvector` for Phase 13 (acceptable at 7k rows). Flag as a Phase 14 optimization if needed.

3. **`/api/votes` filter by `groupe` — is groupe stored on the scrutin or only on individual vote actors?**
   - What we know: `scrutins` table has no `groupe` column. `votes` table links `actor_id → actors.group`. Filtering scrutins by group requires a subquery or join to `votes`.
   - What's unclear: Whether the requirement is "scrutins where a specific group voted a certain way" or just "scrutins where a specific group is involved."
   - Recommendation: Implement `groupe` filter as a query against `votes.actor_id → actors.group` (require that at least one vote from that group exists). Keep it optional for Phase 13 since requirement is vague.

---

## Sources

### Primary (HIGH confidence)
- `nitro.build/config` — openAPI config structure, production modes, ui routes
- `mokkapps.de/blog/document-your-nuxt-endpoints-with-open-api-and-visualize-with-swagger-or-scalar` — full working examples of `defineRouteMeta` with parameters and responses
- Project codebase — existing API endpoint patterns, schema, pagination utils
- `nuxt.com/modules/scalar` — @scalar/nuxt version 0.6.18, Nuxt 3.0.0+ requirement

### Secondary (MEDIUM confidence)
- `orm.drizzle.team/docs/guides/postgresql-full-text-search` — FTS patterns with Drizzle + stored tsvector
- Nitro GitHub discussions #2627 — openAPI configuration object details

### Tertiary (LOW confidence)
- WebSearch results on UNION FTS across multiple tables — patterns are standard PostgreSQL but not Drizzle-specific examples found

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — @scalar/nuxt is the official Nuxt module for Scalar, Nitro openAPI is built-in, both verified with official sources
- Architecture: HIGH — new endpoints follow existing verified project patterns directly; OpenAPI setup is straightforward
- Pitfalls: HIGH — votes pagination and production openAPI disabling are verifiable from docs; UNION total_count is standard PostgreSQL behavior
- Cross-type FTS UNION: MEDIUM — pattern is correct PostgreSQL but no Drizzle-specific UNION example with FTS found; raw SQL approach is safe

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable ecosystem — Nitro/Nuxt release pace is moderate)
