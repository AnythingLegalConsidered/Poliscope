# Phase 16: Cleanup & Polish v2.0 - Research

**Researched:** 2026-04-05
**Domain:** Frontend Vue/Nuxt polish + Python ingestion script removal + sitemap extension
**Confidence:** HIGH — all findings from direct codebase inspection

## Summary

Phase 16 fixes 4 discrete gap-closure items identified in `v2.0-MILESTONE-AUDIT.md`. No new
features, no new dependencies. Each item is a small, self-contained change touching one file
(or two files at most). Total estimated scope: ~100 lines of code across 4 files.

The 4 items are independent and can be executed in any order. The riskiest is item 1 (removing
`ingest_deputies.py` from `run_all.py`) because it changes the default behavior of the pipeline
orchestrator — but the fix is straightforward: make `--skip-deputies` the default, or remove the
step entirely. Items 2, 3, 4 are pure frontend/sitemap additions with zero backend risk.

**Primary recommendation:** Fix all 4 items in a single plan (`16-01-PLAN.md`). No new
dependencies required. All fixes use patterns already present in the codebase.

---

## Item Analysis

### Item 1 — Legacy `ingest_deputies.py` / `run_all.py`

**File:** `packages/ingestion/scripts/ingest_deputies.py`
**Orchestrator:** `packages/ingestion/scripts/run_all.py` (Step 6)

**What the script does:**
- Fetches deputies from `nosdeputes.fr` API
- Upserts into table named `deputies` — a table that no longer exists in the schema
- Schema uses `actors` table instead (unified AN + Senat model from Phase 9)

**Current state in `run_all.py`:**
- Step 6 runs `ingest_deputies.py` by default unless `--skip-deputies` is passed
- If run without `--skip-deputies`, the script errors at DB execute time (table `deputies` does not exist)
- The flag `--skip-deputies` exists and works correctly — but it must be manually specified

**Resolution options (mutually exclusive):**
1. **Remove Step 6 entirely** from `run_all.py` — simplest, cleanest. `ingest_deputies.py` stays as archive.
2. **Change default to skip** — make `skip_deputies` default to `True` in argparse, renaming flag to `--include-deputies`.
3. **Delete the script** — remove `ingest_deputies.py` entirely.

**Recommendation:** Option 1 (remove Step 6 from `run_all.py`, keep the file as dead code with a
deprecation comment). This avoids touching the script itself and is the least disruptive. The audit
requirement is: "run_all.py no longer references a non-existent `deputies` table" — removing the
step satisfies this. Do NOT delete the file yet (it may serve as reference for the data mapping).

**Key code location:**
```python
# run_all.py lines 6, 109, 159-164
# Step 6: Legacy deputies (nosdeputes.fr — kept for backward compat)
if not args.skip_deputies:
    if not run_script("ingest_deputies.py"):
        errors += 1
else:
    logger.info("SKIPPED: ingest_deputies.py (legacy)")
```

---

### Item 2 — `voteStats` not rendered in `deputies/[id].vue`

**File:** `packages/web/app/pages/deputies/[id].vue`

**What the API returns:**
The endpoint `GET /api/deputies/:id` (`packages/web/server/api/deputies/[id].get.ts`) already
fetches and returns `voteStats`:
```typescript
// lines 131-143: voteStats computed and returned
const voteStats = voteStatsRows.map(row => ({
  position: row.position,  // 'for' | 'against' | 'abstain' | 'absent'
  count: Number(row.count),
}))
return { deputy, interventions, tagStats, voteStats }
```

**What the template renders:**
The template has no `voteStats` section at all. `data.value.voteStats` is fetched but silently
dropped. The template renders: header, tagStats pills, interventions list, pagination.

**What to add:**
A vote position breakdown section between the tag stats and interventions list. Pattern from
`pages/votes/[id].vue` shows the badge style already used: positions as colored badges/counts.

**Position values in DB:** `'for'` | `'against'` | `'abstain'` | `'absent'`

**Design system pattern (already in [id].vue):**
- Bronze/10 bg for AN chamber badge → use same palette for vote positions
- `for`: green tone | `against`: red tone | `abstain`: gray | `absent`: muted
- Keep consistent with `parchment / stone-border / bronze` design tokens already in the file

**Render location:** After `displayedTags` section (line ~138), before interventions list (line ~154).

**Data shape to consume:**
```typescript
// data.value.voteStats — already available, no API change needed
[{ position: 'for', count: 423 }, { position: 'against', count: 12 }, ...]
```

---

### Item 3 — `DeputyCard.vue` missing chamber badge

**File:** `packages/web/app/components/DeputyCard.vue`

**Current props:**
```typescript
defineProps<{
  id: number
  fullName: string
  group: string | null
  photoUrl: string | null
  constituency: string | null
}>()
```
No `chamber` prop exists.

**API response for deputies list:**
`GET /api/deputies` (`packages/web/server/api/deputies/index.get.ts`) selects these columns:
`id, officialId, firstName, lastName, fullName, group, photoUrl, constituency, isActive, createdAt, updatedAt`

**Missing:** `chamber` is NOT selected by the index endpoint — it exists in the `actors` schema
(`text('chamber')` — values: `'AN'` | `'Senat'`) but is not included in the select projection.

**Two-file change required:**
1. `index.get.ts` — add `chamber: actors.chamber` to the select
2. `DeputyCard.vue` — add `chamber?: string | null` prop + render badge

**Usage in `index.vue`:**
```html
<DeputyCard v-for="deputy in allDeputies" :key="deputy.id" v-bind="deputy" />
```
Since `v-bind="deputy"` spreads the whole object, adding `chamber` to the API response
automatically passes it to DeputyCard — no change needed in `index.vue`.

**Badge pattern already established** in `deputies/[id].vue` (lines 115-126):
```html
<span v-if="data.deputy?.chamber === 'AN'" class="text-xs bg-bronze/10 text-bronze px-2 py-0.5 rounded-full font-medium">AN</span>
<span v-else-if="data.deputy?.chamber === 'Senat'" class="text-xs bg-ink/10 text-ink px-2 py-0.5 rounded-full font-medium">Sénat</span>
```
Reuse exactly this pattern in `DeputyCard.vue` next to the `GroupBadge`.

---

### Item 4 — Scrutins missing from sitemap

**File:** `packages/web/server/api/__sitemap__/urls.ts`

**Current state:**
```typescript
// Fetches debates + actors → generates /debates/:id and /deputies/:id URLs
// scrutins table is NOT queried
return [...debateUrls, ...deputyUrls]
```

**Scrutins table structure (from schema):**
```typescript
scrutins: { id, officialId, title, date, chamber, ... }
```
Frontend route for scrutins: `/votes/:id` (from `pages/votes/[id].vue`)

**What to add:**
```typescript
import { scrutins } from 'shared/schema'

// In Promise.all — add third query:
db.select({ id: scrutins.id, date: scrutins.date }).from(scrutins).orderBy(asc(scrutins.id))

// Map to URLs:
const scrutinUrls = scrutinRows.map(s => ({
  loc: `/votes/${s.id}`,
  lastmod: s.date ? new Date(s.date).toISOString().split('T')[0] : undefined,
}))

return [...debateUrls, ...deputyUrls, ...scrutinUrls]
```

**Scale consideration:** There are ~7,062 scrutins (5,908 AN + 1,154 Senat). The sitemap module
(@nuxtjs/sitemap 8.0.9 — installed) handles large URL sets via chunking automatically. No
performance concern.

**Import already available:** `scrutins` is exported from `shared/schema` — same import source
already used in the file for `debates` and `actors`.

---

## Standard Stack

No new dependencies for this phase. All patterns use existing stack:

| Tool | Version | Purpose |
|------|---------|---------|
| Nuxt 3 / Vue 3 | Installed | Frontend rendering |
| @nuxtjs/sitemap | 8.0.9 | Sitemap generation (already configured) |
| Drizzle ORM | Installed | DB queries in sitemap + API |
| shared/schema | Local | Drizzle table definitions |
| Python 3 | Installed | Ingestion pipeline |

**Installation:** None needed.

---

## Architecture Patterns

### Pattern 1: Sitemap event handler (nuxtjs/sitemap)
**What:** `defineSitemapEventHandler` — server-side handler that returns URL objects
**Source:** Already implemented in `urls.ts` — extend the existing file, don't create new one
```typescript
// Pattern already in urls.ts
export default defineSitemapEventHandler(async () => {
  const [debateRows, actorRows, scrutinRows] = await Promise.all([...])
  return [...debateUrls, ...deputyUrls, ...scrutinUrls]
})
```

### Pattern 2: Chamber badge in Vue template
**What:** Conditional `<span>` with design-system classes
**When:** When `chamber` prop is `'AN'` or `'Senat'`
**Source:** Directly from `deputies/[id].vue` lines 115-126 — copy verbatim

### Pattern 3: voteStats section in profile template
**What:** Summary of vote positions as count badges
**Source:** Design tokens from `deputies/[id].vue` + `votes/index.vue` color patterns

### Anti-Patterns to Avoid
- **Don't add a `ChamberBadge` component** — the badge is 2 spans, not worth extracting
- **Don't modify `ingest_deputies.py` internals** — the goal is to stop running it, not fix it
- **Don't paginate scrutins in sitemap** — sitemap module handles chunking internally

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Sitemap chunking for 7K+ URLs | Custom pagination | @nuxtjs/sitemap handles it automatically |
| Chamber label mapping | Switch/map utility | Inline v-if/v-else-if (2 values only) |

---

## Common Pitfalls

### Pitfall 1: `index.get.ts` select projection
**What goes wrong:** Adding `chamber` to DeputyCard props but forgetting to add it to the API
select — `v-bind="deputy"` will pass `undefined` silently.
**How to avoid:** Modify `index.get.ts` select FIRST, verify response includes `chamber`, then
update DeputyCard.

### Pitfall 2: `run_all.py` step numbering in comments
**What goes wrong:** Removing Step 6 leaves steps 7-11 with stale numbers in comments.
**How to avoid:** Renumber steps 7→6, 8→7, 9→8, 10→9, 11→10 in comments AND in the `steps` list
for the plan logger. Or just add a comment saying "Step 6 removed — was legacy ingest_deputies.py".

### Pitfall 3: `voteStats` section visible when empty
**What goes wrong:** A parlamentarian with no recorded votes (e.g. new senator) shows an empty
vote section.
**How to avoid:** Wrap the voteStats block in `v-if="data.voteStats?.length > 0"`.

### Pitfall 4: Sitemap `date` field is a PostgreSQL timestamp
**What goes wrong:** Drizzle returns a JS `Date` object, but `.toISOString()` requires it to be
non-null. The `scrutins.date` column is `NOT NULL` — so null check isn't strictly needed, but
apply it anyway for consistency with the existing debate pattern.

---

## Code Examples

### Add chamber to deputies index API
```typescript
// packages/web/server/api/deputies/index.get.ts — add to select:
chamber: actors.chamber,
```

### DeputyCard chamber badge (after GroupBadge)
```html
<!-- Add after <GroupBadge v-if="group" .../> -->
<span
  v-if="chamber === 'AN'"
  class="text-xs bg-bronze/10 text-bronze px-2 py-0.5 rounded-full font-medium"
>AN</span>
<span
  v-else-if="chamber === 'Senat'"
  class="text-xs bg-ink/10 text-ink px-2 py-0.5 rounded-full font-medium"
>Sénat</span>
```

### voteStats section in deputies/[id].vue
```html
<!-- Add after displayedTags section, before interventions list -->
<div v-if="data.voteStats?.length > 0" class="mb-6">
  <h2 class="text-sm font-semibold text-ink mb-2">Votes</h2>
  <div class="flex flex-wrap gap-2">
    <span
      v-for="stat in data.voteStats"
      :key="stat.position"
      class="px-2 py-0.5 rounded-full text-xs border border-stone-border text-ink"
    >
      {{ stat.position }} <span class="text-ink-muted ml-1">{{ stat.count }}</span>
    </span>
  </div>
</div>
```

### Sitemap scrutins addition
```typescript
// packages/web/server/api/__sitemap__/urls.ts
import { asc } from 'drizzle-orm'
import { debates, actors, scrutins } from 'shared/schema'

export default defineSitemapEventHandler(async () => {
  const [debateRows, actorRows, scrutinRows] = await Promise.all([
    db.select({ id: debates.id, date: debates.date }).from(debates).orderBy(asc(debates.id)),
    db.select({ id: actors.id }).from(actors).orderBy(asc(actors.id)),
    db.select({ id: scrutins.id, date: scrutins.date }).from(scrutins).orderBy(asc(scrutins.id)),
  ])
  // ...
  const scrutinUrls = scrutinRows.map(s => ({
    loc: `/votes/${s.id}`,
    lastmod: s.date ? new Date(s.date).toISOString().split('T')[0] : undefined,
  }))
  return [...debateUrls, ...deputyUrls, ...scrutinUrls]
})
```

### run_all.py — remove Step 6
```python
# Remove or comment out Step 6 block (lines ~159-164):
# Step 6 REMOVED — ingest_deputies.py writes to non-existent deputies table
# Use ingest_actors_an.py / ingest_actors_senat.py instead
# Also remove from argparse (--skip-deputies) and from steps[] plan logger
```

---

## Open Questions

1. **voteStats position labels: raw values or localized?**
   - What we know: DB stores `'for'` | `'against'` | `'abstain'` | `'absent'` (English)
   - What's unclear: Whether to render them in French (pour/contre/abstention/absent) or raw
   - Recommendation: Render in French — consistent with rest of UI. Map: `for→Pour`, `against→Contre`, `abstain→Abstention`, `absent→Absent`

2. **DeputyCard `chamber` prop: optional or required?**
   - What we know: All actors in DB have a `chamber` value (set during ingestion)
   - What's unclear: Could an actor have `chamber: null` (e.g. legacy data)?
   - Recommendation: Type as `chamber?: string | null` (optional) to be safe — badge simply won't show if null

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — all findings from reading actual files
- `packages/web/server/api/__sitemap__/urls.ts` — current sitemap implementation
- `packages/web/server/api/deputies/index.get.ts` — confirmed `chamber` missing from select
- `packages/web/server/api/deputies/[id].get.ts` — confirmed `voteStats` returned but not rendered
- `packages/web/app/pages/deputies/[id].vue` — confirmed no voteStats template section
- `packages/web/app/components/DeputyCard.vue` — confirmed no chamber prop
- `packages/ingestion/scripts/run_all.py` — confirmed Step 6 runs ingest_deputies.py by default
- `packages/shared/src/schema.ts` — schema reference for all tables
- `.planning/v2.0-MILESTONE-AUDIT.md` — gap definitions

---

## Metadata

**Confidence breakdown:**
- Item 1 (legacy script): HIGH — code read directly, fix is unambiguous
- Item 2 (voteStats render): HIGH — API confirmed returning data, template confirmed missing section
- Item 3 (chamber badge): HIGH — API select confirmed missing field, prop confirmed missing
- Item 4 (sitemap): HIGH — query pattern directly mirrors existing code, schema confirmed

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable codebase, no fast-moving deps)
