# Phase 3: API Backend - Research

**Researched:** 2026-03-27
**Domain:** Nuxt server routes + Drizzle ORM + PostgreSQL full-text search
**Confidence:** HIGH

## Summary

Phase 3 builds REST API routes in Nuxt's `server/api/` directory using the existing Drizzle ORM setup with postgres-js driver. The project already has a working DB connection utility (`server/utils/db.ts`), schema with proper indexes (including a GIN full-text search index on `interventions.content`), and a health check endpoint as reference pattern.

The main technical challenges are: (1) implementing full-text search via Drizzle's `sql` template since FTS is not natively supported, (2) pagination with total count, and (3) joining across tables (interventions -> deputies, interventions -> tags). All of these are well-supported through Drizzle's SQL builder and documented patterns.

**Primary recommendation:** Build 6 API endpoints using Drizzle's select builder with `sql` template for FTS. Use offset/limit pagination with `count(*) over()` window function for efficient single-query pagination. Use `websearch_to_tsquery('french', ...)` for the search endpoint to safely handle user input.

## Current Project State

### Server Directory Structure
```
server/
├── api/
│   └── health.get.ts          # Existing health check endpoint
├── db/
│   └── schema.ts              # Full schema (deputies, debates, interventions, tags, intervention_tags)
└── utils/
    └── db.ts                  # Drizzle client export (postgres-js driver)
```

### DB Connection (server/utils/db.ts)
```typescript
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from '../db/schema'

const client = postgres(useRuntimeConfig().databaseUrl)
export const db = drizzle(client, { schema })
```

- **Auto-imported** by Nuxt in all `server/` files (no explicit import needed)
- Uses `useRuntimeConfig().databaseUrl` which maps from `NUXT_DATABASE_URL` env var
- Schema is passed to drizzle, enabling relational query API (`db.query.*`)

### Database Schema Summary

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `deputies` | id, officialId, firstName, lastName, fullName, group (political_group), photoUrl, constituency, isActive | 618 rows |
| `debates` | id, officialId, title, date, legislature, sessionType, sourceUrl | 5 rows |
| `interventions` | id, debateId, deputyId, speakerName, speakerRole, content, orderInDebate | 2479 rows, GIN FTS index |
| `tags` | id, name, slug | 12 rows |
| `intervention_tags` | interventionId, tagId | 787 rows, composite PK |

### Installed Dependencies
- `drizzle-orm` ^0.45.1
- `postgres` ^3.4.8 (postgres-js driver)
- `drizzle-kit` ^0.31.10 (dev)
- No additional packages needed for API routes

### Potential Blocker: .env Configuration
The `.env` file only has `DATABASE_URL` but NOT `NUXT_DATABASE_URL`. The `.env.example` has both. The `server/utils/db.ts` uses `useRuntimeConfig().databaseUrl` which requires `NUXT_DATABASE_URL`. If the health endpoint works in dev, Nuxt may be picking it up anyway, but this should be verified. The first API plan should ensure `.env` has `NUXT_DATABASE_URL`.

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| drizzle-orm | ^0.45.1 | SQL query builder + ORM | Already configured with schema |
| postgres | ^3.4.8 | PostgreSQL driver (postgres-js) | Already used in db.ts |
| Nuxt (Nitro/H3) | ^4.4.2 | Server route framework | Built-in, defineEventHandler, getQuery, getRouterParam |

### No Additional Packages Needed
All API functionality can be built with existing deps:
- `getQuery(event)` for query parameters (from H3, auto-imported)
- `getRouterParam(event, 'id')` for route params (from H3, auto-imported)
- `createError()` for error responses (from H3, auto-imported)
- `sql` template from drizzle-orm for raw SQL (FTS)
- `count`, `eq`, `desc`, `asc`, `and`, `or`, `like`, `ilike` from drizzle-orm

### Optional: Validation Library
| Library | Purpose | When to Use |
|---------|---------|-------------|
| zod | Input validation | If strict query param validation is desired |

For now, manual validation is fine given the simple query params. Zod can be added later if needed.

## Architecture Patterns

### Recommended API Route Structure
```
server/
├── api/
│   ├── health.get.ts                    # [EXISTS] Health check
│   ├── debates/
│   │   ├── index.get.ts                 # GET /api/debates (list, paginated)
│   │   └── [id].get.ts                  # GET /api/debates/:id (detail + interventions)
│   ├── deputies/
│   │   ├── index.get.ts                 # GET /api/deputies (list, paginated)
│   │   └── [id].get.ts                  # GET /api/deputies/:id (profile + interventions)
│   └── search.get.ts                    # GET /api/search (full-text search)
├── db/
│   └── schema.ts                        # [EXISTS]
└── utils/
    ├── db.ts                            # [EXISTS] Drizzle client
    └── pagination.ts                    # [NEW] Shared pagination helper
```

### Pattern 1: Paginated List Endpoint
**What:** Standard offset/limit pagination returning data + metadata
**When to use:** All list endpoints (debates, deputies, search results)

```typescript
// server/utils/pagination.ts
export function getPaginationParams(query: Record<string, string | undefined>) {
  const page = Math.max(1, parseInt(query.page || '1', 10))
  const limit = Math.min(100, Math.max(1, parseInt(query.limit || '20', 10)))
  const offset = (page - 1) * limit
  return { page, limit, offset }
}

export function paginatedResponse<T>(data: T[], total: number, page: number, limit: number) {
  return {
    data,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  }
}
```

### Pattern 2: Count with Window Function
**What:** Get total count alongside paginated results in a single query
**When to use:** When you want to avoid a second COUNT(*) query

```typescript
// Using sql`count(*) over()` window function
import { sql, eq } from 'drizzle-orm'

const results = await db
  .select({
    id: debates.id,
    title: debates.title,
    date: debates.date,
    totalCount: sql<number>`count(*) over()`,
  })
  .from(debates)
  .orderBy(desc(debates.date))
  .limit(limit)
  .offset(offset)

const total = results[0]?.totalCount ?? 0
```

### Pattern 3: Event Handler with Error Handling
**What:** Standard Nuxt API route pattern
**When to use:** Every endpoint

```typescript
// server/api/debates/index.get.ts
export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const { page, limit, offset } = getPaginationParams(query)

  try {
    // ... db query
    return paginatedResponse(data, total, page, limit)
  } catch (error) {
    throw createError({
      statusCode: 500,
      message: 'Failed to fetch debates',
    })
  }
})
```

### Pattern 4: Route Parameter Endpoint
**What:** Single resource by ID
**When to use:** Detail endpoints (debates/:id, deputies/:id)

```typescript
// server/api/debates/[id].get.ts
export default defineEventHandler(async (event) => {
  const id = Number(getRouterParam(event, 'id'))
  if (isNaN(id)) {
    throw createError({ statusCode: 400, message: 'Invalid debate ID' })
  }

  const debate = await db.select().from(debates).where(eq(debates.id, id)).limit(1)
  if (!debate.length) {
    throw createError({ statusCode: 404, message: 'Debate not found' })
  }

  // Fetch related interventions
  const debateInterventions = await db
    .select()
    .from(interventions)
    .where(eq(interventions.debateId, id))
    .orderBy(asc(interventions.orderInDebate))

  return { ...debate[0], interventions: debateInterventions }
})
```

### Anti-Patterns to Avoid
- **N+1 queries:** Don't fetch list then loop to fetch related data. Use joins or batch queries.
- **Unbounded queries:** Always enforce limit (max 100) even if client doesn't send one.
- **String concatenation in SQL:** Always use Drizzle's `sql` template for interpolation to prevent SQL injection.
- **Returning raw DB rows:** Map column names to camelCase API response format (Drizzle already does this via schema column mapping).

## Full-Text Search Implementation

### Approach: websearch_to_tsquery with Existing GIN Index

The DB already has a GIN index: `to_tsvector('french', content)` on `interventions`.

**Critical:** The tsquery language config MUST match the tsvector index language (`'french'`).

```typescript
// server/api/search.get.ts
import { sql, eq, and, desc } from 'drizzle-orm'
import { interventions, deputies, debates } from '~/server/db/schema'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const q = (query.q as string || '').trim()

  if (!q) {
    throw createError({ statusCode: 400, message: 'Search query required' })
  }

  const { page, limit, offset } = getPaginationParams(query)

  // Optional filters
  const deputyId = query.deputyId ? Number(query.deputyId) : null
  const debateId = query.debateId ? Number(query.debateId) : null

  // Build WHERE conditions
  const conditions = [
    sql`to_tsvector('french', ${interventions.content}) @@ websearch_to_tsquery('french', ${q})`,
  ]
  if (deputyId) conditions.push(eq(interventions.deputyId, deputyId))
  if (debateId) conditions.push(eq(interventions.debateId, debateId))

  const results = await db
    .select({
      id: interventions.id,
      content: interventions.content,
      speakerName: interventions.speakerName,
      debateId: interventions.debateId,
      deputyId: interventions.deputyId,
      debateTitle: debates.title,
      debateDate: debates.date,
      rank: sql<number>`ts_rank(to_tsvector('french', ${interventions.content}), websearch_to_tsquery('french', ${q}))`,
      headline: sql<string>`ts_headline('french', ${interventions.content}, websearch_to_tsquery('french', ${q}), 'MaxWords=50, MinWords=20, StartSel=<mark>, StopSel=</mark>')`,
      totalCount: sql<number>`count(*) over()`,
    })
    .from(interventions)
    .leftJoin(debates, eq(interventions.debateId, debates.id))
    .where(and(...conditions))
    .orderBy(sql`ts_rank(to_tsvector('french', ${interventions.content}), websearch_to_tsquery('french', ${q})) DESC`)
    .limit(limit)
    .offset(offset)

  const total = results[0]?.totalCount ?? 0
  return paginatedResponse(
    results.map(({ totalCount, ...r }) => r),
    total,
    page,
    limit,
  )
})
```

### Key FTS Functions
| Function | Purpose | When to Use |
|----------|---------|-------------|
| `websearch_to_tsquery('french', input)` | Safely parses user input with AND/OR/NOT/"quotes" | **Default for user search** -- handles messy input |
| `plainto_tsquery('french', input)` | Treats all words as AND | When exact match on all words is needed |
| `ts_rank(tsvector, tsquery)` | Relevance score | Ordering results by relevance |
| `ts_headline('french', text, query, options)` | Highlighted snippet | Showing matched excerpt in results |

### Why websearch_to_tsquery (not to_tsquery)
- `to_tsquery` requires pre-formatted input (`word1 & word2 | word3`) -- crashes on raw user input
- `websearch_to_tsquery` accepts natural language (`"famille politique" immigration OR securite`) -- safe for user-facing search
- Available since PostgreSQL 11 (our Docker image is recent)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL query building | String concatenation | Drizzle `sql` template | SQL injection prevention |
| Pagination math | Custom offset calculation | Shared `getPaginationParams` utility | DRY, consistent across endpoints |
| Full-text parsing | Custom tokenizer/stemmer | PostgreSQL `websearch_to_tsquery('french')` | French stemming, stop words, accent handling built-in |
| Search highlighting | Regex-based highlighting | PostgreSQL `ts_headline()` | Handles stemmed matches correctly |
| API response format | Ad-hoc response shapes | Shared `paginatedResponse` utility | Consistent API contract |

## Common Pitfalls

### Pitfall 1: FTS Language Mismatch
**What goes wrong:** Search returns no results despite data existing.
**Why it happens:** Using `'english'` in tsquery but index uses `'french'`. The stemming algorithms differ.
**How to avoid:** Always use `'french'` in ALL FTS functions (tsvector, tsquery, headline). Match the GIN index exactly.
**Warning signs:** Empty search results for common French words.

### Pitfall 2: Missing NUXT_DATABASE_URL
**What goes wrong:** Server routes fail with empty database URL.
**Why it happens:** `.env` has `DATABASE_URL` (for drizzle-kit) but not `NUXT_DATABASE_URL` (for runtime config).
**How to avoid:** Ensure `.env` has both variables. Verify with health endpoint before building new routes.
**Warning signs:** `useRuntimeConfig().databaseUrl` returns empty string.

### Pitfall 3: Unbounded Query Results
**What goes wrong:** Memory spikes or slow responses on large datasets.
**Why it happens:** No default limit on list queries.
**How to avoid:** Always enforce `limit` with a max cap (100). Default to 20.

### Pitfall 4: to_tsquery Crashes on User Input
**What goes wrong:** PostgreSQL throws syntax error on search.
**Why it happens:** `to_tsquery` expects formatted input (`word1 & word2`). Raw user input like `"hello world"` is invalid syntax.
**How to avoid:** Use `websearch_to_tsquery` which safely handles any user input.

### Pitfall 5: N+1 Queries on Detail Endpoints
**What goes wrong:** Deputies detail page makes 1 query for deputy + N queries for each intervention's tags.
**Why it happens:** Fetching tags per intervention in a loop.
**How to avoid:** Fetch all intervention IDs first, then batch-query tags with `IN (...)` clause, then merge in JS.

### Pitfall 6: count(*) over() Returns String
**What goes wrong:** TypeScript types pagination total as string instead of number.
**Why it happens:** postgres-js returns bigint/string for count aggregates.
**How to avoid:** Cast explicitly: `sql<number>\`count(*)::int over()\`` or use `Number()` on the result.

## Recommended Plan Breakdown

### Plan 03-01: Foundation + Debates Endpoints (Wave 1)
- Verify/fix `.env` has `NUXT_DATABASE_URL`
- Create `server/utils/pagination.ts` (shared helper)
- `GET /api/debates` -- paginated list, ordered by date desc
- `GET /api/debates/:id` -- debate detail with interventions (ordered by orderInDebate)
- Verification: curl tests against running dev server

### Plan 03-02: Deputies Endpoints (Wave 2)
- `GET /api/deputies` -- paginated list, filterable by group, search by name
- `GET /api/deputies/:id` -- deputy profile + their interventions (paginated) + tags
- Verification: curl tests

### Plan 03-03: Search Endpoint (Wave 3)
- `GET /api/search` -- full-text search with `websearch_to_tsquery('french', ...)`
- Filters: deputyId, debateId, tag
- Ranking with `ts_rank`, snippets with `ts_headline`
- Paginated results with joined debate/deputy info
- Verification: curl tests with French search terms

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Drizzle relational queries only | Mix of select builder + sql template | drizzle-orm 0.30+ | FTS requires sql template, not relational API |
| `to_tsquery` for user search | `websearch_to_tsquery` | PostgreSQL 11+ | Safe user input handling |
| Separate count query | `count(*) over()` window function | Always available | Single query for data + count |

## Open Questions

1. **Tag filtering on search/deputies**
   - What we know: `intervention_tags` table exists with tag associations
   - What's unclear: Should search allow filtering by tag slug? Should deputies endpoint show tag distribution?
   - Recommendation: Include tag filter on search endpoint. Defer tag analytics to a later phase.

2. **Response shape for nested data**
   - What we know: Detail endpoints need related data (debate -> interventions, deputy -> interventions)
   - What's unclear: How deep should nesting go? Should interventions include their tags?
   - Recommendation: Include tags on detail endpoints but not on list endpoints (performance).

3. **CORS / Rate limiting**
   - What we know: API is internal (same Nuxt app serves frontend + API)
   - What's unclear: Will there be external API consumers?
   - Recommendation: Defer CORS/rate limiting. Same-origin requests don't need CORS.

## Sources

### Primary (HIGH confidence)
- [Drizzle ORM - PostgreSQL Full-Text Search Guide](https://orm.drizzle.team/docs/guides/postgresql-full-text-search) - FTS patterns, sql template usage
- [Drizzle ORM - Limit/Offset Pagination](https://orm.drizzle.team/docs/guides/limit-offset-pagination) - Pagination patterns
- [Drizzle ORM - Select](https://orm.drizzle.team/docs/select) - count(), joins, aggregates
- Project source code: `server/utils/db.ts`, `server/db/schema.ts`, `server/api/health.get.ts`

### Secondary (MEDIUM confidence)
- [Drizzle ORM - Magic sql operator](https://orm.drizzle.team/docs/sql) - sql template documentation
- [Nuxt Server Routes](https://nuxt.com/docs/guide/directory-structure/server) - getQuery, getRouterParam, defineEventHandler

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All deps already installed and configured
- Architecture: HIGH - Patterns follow Nuxt conventions, verified against existing health endpoint
- FTS implementation: HIGH - Verified with official Drizzle docs, GIN index already exists
- Pitfalls: HIGH - Based on known PostgreSQL/Drizzle behavior

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable stack, no fast-moving dependencies)
