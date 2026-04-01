# Phase 14: Frontend Votes, Sénat & Bicameral - Research

**Researched:** 2026-04-01
**Domain:** Nuxt 3 frontend — new pages (votes list, vote detail, senator profiles) + bicameral navigation
**Confidence:** HIGH (codebase fully audited, no external library uncertainty)

## Summary

Phase 14 is a pure frontend phase: it adds pages for scrutins/votes and makes the senator experience equivalent to deputies. The API layer (Phase 13) is complete — all needed endpoints exist and are stable. No new backend work is required. The work is:
1. Three new page routes: `/votes` (list), `/votes/[id]` (detail), and extending `/deputies/[id]` to work for senators.
2. Three new or updated components: `ScrutinCard.vue`, `ScrutinResultBar.vue`, a `VotePositionBadge.vue`.
3. Updating the search page to render `scrutin`-type results distinctively (already in API response, not yet in UI).
4. Updating the debates page and deputies page to show chamber filter tabs — the debates page already has this pattern (implemented in Phase 11). Deputies page does not yet have it.
5. Adding a `/votes` nav link to the layout header.

The existing codebase has a very clear, consistent pattern: `useFetch` + infinite scroll via `useIntersectionObserver` + chamber filter tabs using pill buttons. Every new page must follow this exact pattern. The design system (marble/bronze/ink, Cinzel headings, no shadows) is already established and should be replicated.

The most nuanced task is the vote detail page (`/votes/[id]`): it shows per-actor vote positions (for/against/abstain/absent) for a scrutin with potentially hundreds of voters. The API response is paginated (1.3M total votes in DB). A tab-filter by position (Pour / Contre / Abstention / Absent) combined with infinite scroll is the right UX pattern, matching how the deputy profile page handles paginated interventions.

**Primary recommendation:** Follow existing page patterns exactly — useFetch + IntersectionObserver infinite scroll + chamber pill tabs. Create ScrutinCard and vote position visualization as new components. Senators use the existing deputies profile page with no route change (actors table is unified).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Nuxt 3 | 4.4.2 (already in project) | Pages, routing, SSR | Already used |
| `@vueuse/core` | 14.2.1 (already in project) | `useIntersectionObserver` for infinite scroll | Already used in every list page |
| Tailwind CSS v4 | 4.2.2 (already in project) | Styling | Already used |
| Drizzle ORM | 0.45.1 (already in project) | Server-side (not needed for new pages) | Already used |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@vueuse/core` `watchDebounced` | Already installed | Debounce search inputs | Search within vote list (if added) |
| Vue 3 `computed` / `ref` / `watch` | Built-in | Reactive state | All filter state |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Infinite scroll (IntersectionObserver) | Pagination buttons | Project pattern is infinite scroll — don't deviate |
| Pill button tabs for chamber filter | `<select>` dropdown | Tabs are the established pattern on debates/index.vue |
| `v-html` for FTS highlight | Custom highlight component | `v-html` already used in SearchResultCard, mark CSS already in main.css |

**Installation:** No new packages needed. Everything is already in `packages/web/package.json`.

---

## Architecture Patterns

### Recommended Project Structure
```
packages/web/app/
├── pages/
│   ├── votes/
│   │   ├── index.vue         # NEW: /votes — list scrutins with chamber/result/date filters
│   │   └── [id].vue          # NEW: /votes/[id] — scrutin detail + paginated per-actor votes
│   ├── deputies/
│   │   ├── index.vue         # UPDATE: add chamber filter tabs (AN/Sénat/Tous)
│   │   └── [id].vue          # MINIMAL UPDATE: display senator chamber badge (already works)
│   ├── search.vue            # UPDATE: render scrutin-type results with VoteResultBadge
│   └── index.vue             # no change needed (debates already have chamber filter)
├── components/
│   ├── ScrutinCard.vue       # NEW: card for vote list page
│   ├── VotePositionBadge.vue # NEW: coloured badge (Pour/Contre/Abstention/Absent)
│   ├── ScrutinResultBar.vue  # NEW: horizontal bar showing for/against/abstain ratios
│   └── SearchResultCard.vue  # UPDATE: add scrutin variant rendering
├── layouts/
│   └── default.vue           # UPDATE: add "Votes" nav link
└── utils/
    └── groupColors.ts        # no change needed
```

### Pattern 1: List page with chamber filter + infinite scroll
**What:** Standard pattern for all list pages in this project.
**When to use:** votes/index.vue, updates to deputies/index.vue

```vue
// Source: packages/web/app/pages/index.vue (debates list — the reference implementation)
const chamber = ref<string | undefined>(undefined)
const page = ref(1)
const allItems = ref<any[]>([])
const sentinel = useTemplateRef('sentinel')

const { data, status } = await useFetch('/api/votes', {
  query: { page, limit: 20, chamber },
  lazy: true,
  watch: [page, chamber],
})

// Reset on filter change
function selectChamber(newVal: string | undefined) {
  page.value = 1
  allItems.value = []
  chamber.value = newVal
}

// Append on page change
watch(data, (newData) => {
  if (newData?.data?.length > 0) allItems.value.push(...newData.data)
}, { immediate: true })

useIntersectionObserver(sentinel, ([entry]) => {
  if (entry?.isIntersecting && status.value !== 'pending' && hasMore.value) {
    page.value++
  }
}, { rootMargin: '200px' })
```

### Pattern 2: Detail page with position tab filter + paginated votes
**What:** Vote detail page needs a position filter (Pour/Contre/Abstention/Absent) on top of pagination.
**When to use:** votes/[id].vue

```vue
// Adapted from deputies/[id].vue (tag filter pattern)
const position = ref<string | null>(null)
const page = ref(1)
const allVotes = ref<any[]>([])

const { data, status } = await useFetch(`/api/votes/${id}`, {
  query: { page, limit: 50, position },
  watch: [page, position],
})

// Reset votes list when position filter changes
watch(position, () => {
  allVotes.value = []
  page.value = 1
})

// Append new page results
watch(data, (newData) => {
  if (!newData?.votes?.data) return
  if (page.value === 1) {
    allVotes.value = newData.votes.data
  } else {
    allVotes.value.push(...newData.votes.data)
  }
}, { immediate: true })
```

API response shape for `/api/votes/[id]`:
```typescript
{
  scrutin: { id, officialId, title, date, chamber, scrutinType, result, votesFor, votesAgainst, votesAbstain, sourceUrl },
  votes: {
    data: [{ id, actorId, position, actorFullName, actorGroup, actorPhotoUrl }],
    pagination: { page, limit, total, totalPages }
  }
}
```

### Pattern 3: SearchResultCard scrutin variant
**What:** The search API already returns `type: 'scrutin'` items with `title`, `result`, `votesFor/Against/Abstain`, `chamber`, `highlight`. The current SearchResultCard renders all results as interventions (it ignores the `type` field).
**When to use:** search.vue + SearchResultCard.vue update

The fix: in `SearchResultCard.vue`, branch on a `type` prop:
```vue
// SearchResultCard update — add type prop
const props = defineProps<{
  type?: 'intervention' | 'scrutin'
  // ... existing props
  // scrutin-specific (optional):
  title?: string
  result?: string | null
  votesFor?: number | null
  votesAgainst?: number | null
  votesAbstain?: number | null
}>()
```
Scrutin results link to `/votes/:id` (context_id = scrutin.id from API).

### Pattern 4: Chamber filter on deputies list
**What:** `/deputies` currently shows all actors (deputies + senators combined). It needs the same pill-button tab pattern as debates/index.vue.
**Reference:** `packages/web/app/pages/index.vue` lines 65-103 (chamber tabs).
**Note:** The API already supports `?chamber=AN|Senat` — just need to add the UI.

### Pattern 5: Senator profile
**What:** A senator accessed via `/deputies/[id]` should work already (same `actors` table, same API endpoint). The only missing piece: the profile page header shows "Assemblée nationale" style info (constituency, group) without indicating it is a senator. Add a chamber badge next to the group badge.
**Change needed:** In `deputies/[id].vue` header section, add `<ChamberBadge :chamber="data.deputy.chamber" />` next to `GroupBadge`.

### Anti-Patterns to Avoid
- **Creating a separate `/senators` route:** Senators use the same actors table and the same deputies detail page. Adding a `/senators/[id]` route would be redundant duplication. Route stays at `/deputies/[id]` for all actors.
- **Fetching all vote positions at once:** The `/api/votes/[id]` endpoint is paginated precisely because there can be 500-900 voters per scrutin. Never attempt to load all at once.
- **A global chamber state/composable:** The chamber filter is local page state on each list page (debates, deputies, votes). There is no need for a global store or composable — keep it local `ref`.
- **Replacing v-html for highlights:** The search uses `v-html` for FTS highlights (`<mark>` tags). The CSS in `main.css` handles the `mark` styling. Don't reinvent this.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vote ratio bar visualization | Custom SVG chart | Simple CSS flexbox `width` percentages | 3 values (for/against/abstain), no library needed |
| Infinite scroll | Custom scroll event listener | `useIntersectionObserver` from `@vueuse/core` | Already in project, handles all edge cases |
| Position color coding | Custom color mapping | Inline Tailwind color classes (green/red/gray/ink) | Simple 4-value enum, no dynamic mapping needed |
| Search input debounce | `setTimeout` + `clearTimeout` | `watchDebounced` from `@vueuse/core` | Already used in search.vue |
| Group badge for senators | New component | Reuse `GroupBadge.vue` | Senate political groups use same format |

**Key insight:** The project has zero charting libraries installed and doesn't need one. A vote result bar is just 3 divs with `flex` and percentage widths — `votesFor / (votesFor + votesAgainst + votesAbstain) * 100`.

---

## Common Pitfalls

### Pitfall 1: Stale allVotes/allItems on filter reset
**What goes wrong:** When `position` or `chamber` filter changes, the accumulated array from previous pages is not cleared. The new page 1 results are pushed onto stale data, producing duplicates.
**Why it happens:** The `watch(data, ...)` handler appends unconditionally.
**How to avoid:** Follow the exact reset pattern from `deputies/index.vue` (lines 41-45): `watch([filters], () => { allItems.value = []; page.value = 1 })`. Also guard in the data watcher: `if (page.value === 1) { allItems.value = newData.data } else { allItems.value.push(...) }`.
**Warning signs:** Duplicate cards appearing when switching filter tabs.

### Pitfall 2: Hydration mismatch from date formatting
**What goes wrong:** Using `new Date().toLocaleDateString()` without explicit `timeZone` causes SSR/client mismatch.
**Why it happens:** Server (UTC) and client (local timezone) format differently.
**How to avoid:** Always use `new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long', timeZone: 'Europe/Paris' })`. This is already done correctly in all existing pages — copy-paste the pattern.
**Warning signs:** Vue hydration warning in browser console.

### Pitfall 3: SearchResultCard type discrimination gap
**What goes wrong:** Scrutin results from `/api/search` are already returned but the current `SearchResultCard` renders them as if they were interventions (looking for `speakerName`, `debate`, `tags` which scrutins don't have).
**Why it happens:** The card was written before cross-type search existed.
**How to avoid:** Add `type` prop and conditional template branches. The `context_id` field from the API is the scrutin's `id` when `type === 'scrutin'` — use it as `to="/votes/:context_id"`.
**Warning signs:** Scrutin search results showing "undefined" for speaker name, broken debate link.

### Pitfall 4: Senator group colors missing
**What goes wrong:** `groupColors.ts` only contains AN political groups (RN, EPR, LFI-NFP, SOC, etc.) from the 17th legislature. Senate group acronyms differ (e.g., "GEST", "LR", "UC", "RDPI").
**Why it happens:** The utility was populated for AN only.
**How to avoid:** Add Senate group entries to `GROUP_MAP` in `groupColors.ts`. At minimum add a graceful fallback (the function already returns `#6b7280` for unknown groups — this is acceptable).
**Warning signs:** All senator group badges showing gray color.

### Pitfall 5: `definePageMeta validate` rejecting non-numeric IDs
**What goes wrong:** Both existing detail pages (`debates/[id].vue`, `deputies/[id].vue`) have `validate: route => /^\d+$/.test(...)`. If the votes detail page omits this, non-numeric slugs will 500 instead of 404.
**Why it happens:** Missing guard.
**How to avoid:** Include the same `definePageMeta({ validate: ... })` in `votes/[id].vue`.

---

## Code Examples

### ScrutinCard component structure
```vue
<!-- Source: pattern from DebateCard.vue -->
<script setup lang="ts">
const props = defineProps<{
  id: number
  title: string
  date: string
  chamber: string | null
  result: string | null          // 'adopted' | 'rejected' | null
  votesFor: number | null
  votesAgainst: number | null
  votesAbstain: number | null
  scrutinType: string | null
}>()

const formattedDate = computed(() => {
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(props.date))
})

const resultLabel = computed(() => {
  if (props.result === 'adopted') return 'Adopté'
  if (props.result === 'rejected') return 'Rejeté'
  return null
})
</script>
```

### Vote result bar (no library needed)
```vue
<!-- Simple CSS ratio bar -->
<script setup lang="ts">
const props = defineProps<{ votesFor: number; votesAgainst: number; votesAbstain: number }>()
const total = computed(() => (props.votesFor ?? 0) + (props.votesAgainst ?? 0) + (props.votesAbstain ?? 0))
const pctFor = computed(() => total.value > 0 ? (props.votesFor / total.value * 100).toFixed(1) : 0)
const pctAgainst = computed(() => total.value > 0 ? (props.votesAgainst / total.value * 100).toFixed(1) : 0)
const pctAbstain = computed(() => total.value > 0 ? (props.votesAbstain / total.value * 100).toFixed(1) : 0)
</script>
<template>
  <div class="flex h-2 rounded-full overflow-hidden">
    <div class="bg-green-500" :style="{ width: pctFor + '%' }" />
    <div class="bg-terracotta" :style="{ width: pctAgainst + '%' }" />
    <div class="bg-stone-border" :style="{ width: pctAbstain + '%' }" />
  </div>
</template>
```

### Nav layout update
```vue
<!-- Source: packages/web/app/layouts/default.vue — add Votes link -->
<nav class="flex items-center gap-6 text-sm text-ink-muted">
  <NuxtLink to="/" active-class="text-bronze" ...>Débats</NuxtLink>
  <NuxtLink to="/votes" active-class="text-bronze" ...>Votes</NuxtLink>
  <NuxtLink to="/deputies" active-class="text-bronze" ...>Parlementaires</NuxtLink>
  <NuxtLink to="/search" active-class="text-bronze" ...>Recherche</NuxtLink>
</nav>
```

Note: "Députés" → "Parlementaires" rename is optional but semantically more accurate once senators are included.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AN-only deputies list | Universal actors table with `chamber` field | Phase 10 | Deputies and senators are in the same table/endpoint |
| Debates AN-only | `chamber` field on debates/interventions/actors | Phase 11 | Frontend chamber filter already implemented for debates |
| Search interventions only | Cross-type UNION search (interventions + scrutins) | Phase 13 | SearchResultCard must handle both types |
| No vote data | Full scrutins + votes tables | Phase 12-13 | Vote list and detail pages are unblocked |

**Deprecated/outdated:**
- The nav link "Députés" is technically inaccurate once senators are navigable — rename to "Parlementaires" is recommended but not required.
- The deputies list page title "Députés de l'Assemblée nationale" becomes inaccurate when showing senators — should be made dynamic like the debates page title.

---

## Open Questions

1. **Senate group color coverage**
   - What we know: `groupColors.ts` has 11 AN groups. Senate has different group abbreviations.
   - What's unclear: What are the actual group abbreviations in the DB for senators ingested in Phase 10?
   - Recommendation: Check `SELECT DISTINCT political_group FROM actors WHERE chamber = 'Senat'` on the live DB. Add missing entries to `GROUP_MAP`. Fallback gray is already safe.

2. **Nav rename: "Députés" → "Parlementaires"**
   - What we know: The page at `/deputies` now shows all actors (deputies + senators).
   - What's unclear: Whether the user wants to rename the nav link and page title.
   - Recommendation: Rename to "Parlementaires" in the nav and deputies list heading — it is a one-liner change and more accurate. Flag as a decision for the planner.

3. **Votes page URL: `/votes` vs `/scrutins`**
   - What we know: The API endpoint is `/api/votes`. French term is "scrutins".
   - What's unclear: User preference for URL slug.
   - Recommendation: Use `/votes` — it is the English-friendly URL and matches the API path. French label in the UI can still say "Scrutins" or "Votes".

4. **Date range filter on votes list**
   - What we know: The API supports `dateFrom` and `dateTo` query params.
   - What's unclear: Whether the UI should expose date pickers.
   - Recommendation: Keep Phase 14 simple — chamber filter + result filter (Adopté/Rejeté/Tous). Skip date pickers to reduce scope. Date filtering can be Phase 15+.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase audit: `packages/web/` — all pages, components, layouts, API endpoints, schema read directly
- `packages/web/server/api/votes/index.get.ts` — exact API response shape verified
- `packages/web/server/api/votes/[id].get.ts` — exact vote detail shape verified
- `packages/web/server/api/search.get.ts` — cross-type response shape verified (scrutin branch)
- `packages/web/server/api/deputies/index.get.ts` — chamber filter already implemented
- `packages/web/app/pages/index.vue` — chamber filter tab pattern (reference implementation)
- `packages/web/app/pages/deputies/index.vue` — infinite scroll + filter reset pattern
- `packages/web/app/pages/search.vue` — watchDebounced + URL sync pattern
- `packages/shared/src/schema.ts` — actors, scrutins, votes table structure

### Secondary (MEDIUM confidence)
- n/a — no external library research needed (all dependencies already in project)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, everything already installed and used
- Architecture: HIGH — all patterns are exact copies/extensions of existing pages
- Pitfalls: HIGH — identified from direct code inspection of existing implementations

**Research date:** 2026-04-01
**Valid until:** Stable — no external libraries to deprecate. Valid until API shape changes.
