# Phase 5: Profils Deputes - Research

**Researched:** 2026-03-28
**Domain:** Nuxt 4 UI, deputy profile page, intervention list with filtering, bidirectional navigation
**Confidence:** HIGH

## Summary

Phase 5 is a UI-only phase. All API infrastructure is already complete: `GET /api/deputies` (list with search/group filter), `GET /api/deputies/:id` (deputy + paginated interventions + tagStats). No new API endpoints are needed. The phase consists of three deliverables: a deputies list page (`/deputies`), a deputy profile page (`/deputies/[id]`), and bidirectional navigation between debate threads and deputy profiles.

The deputy profile page has a well-defined data shape from the existing API: `deputy` object (name, group, photo, constituency), `interventions` paginated list (each with embedded debate info: title + date), and `tagStats` array (tag name, slug, count). The profile page should display a stat header, tag distribution, and a paginated/filterable intervention list — all from a single `useFetch` call. The intervention list reuses the existing `InterventionCard` component with a new `debateLink` prop to navigate to the debate.

Filtering on the client side (by tag) is appropriate at this scale — no additional API filter endpoint needed. The `@vueuse/core` package already in the project provides `useIntersectionObserver` if infinite scroll is desired for interventions, but simple pagination with a "load more" button is equally valid given the profile page is less scroll-heavy than the debates list.

**Primary recommendation:** Build `/deputies` (list page), `/deputies/[id]` (profile page) using the existing API shape. Reuse `InterventionCard` with an added debate navigation link. Client-side tag filtering via computed ref. No new dependencies required.

## Standard Stack

### Core (all already installed — zero new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nuxt | ^4.4.2 | File-based routing, SSR, auto-imports | Already in project |
| vue | ^3.5.30 | Composition API, computed, ref | Already in project |
| tailwindcss | ^4.2.2 | Marbre & Bronze design tokens | Already in project |
| @vueuse/core | ^14.2.1 | `useIntersectionObserver` if infinite scroll on interventions | Already installed |

### No new installations needed

All required functionality is covered by existing dependencies. No additional packages to install.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Client-side tag filtering (computed) | API-side filter param | API already returns tagStats; adding `?tag=` param to deputies/:id would require API change. Not needed at this scale (20 items per page) |
| Simple "load more" button for interventions | Infinite scroll | Infinite scroll is already proven from debates list; either works, but load-more is simpler for profile page UX |
| Reuse `InterventionCard` with new prop | Separate `ProfileInterventionCard` | Prop extension is less code; only need debate title/date link added |

## Architecture Patterns

### File additions for this phase

```
app/
├── pages/
│   ├── deputies/
│   │   ├── index.vue          # Deputies list with search + group filter
│   │   └── [id].vue           # Deputy profile page
│   └── (existing)
├── components/
│   └── DeputyCard.vue         # Card for list page (name, group, photo, constituency)
```

No new composables, no new utils, no new API routes.

### Pattern 1: Deputy Profile Page — Single useFetch, client-side filtering

**What:** Fetch deputy + interventions + tagStats in one call. Store active tag filter in `ref`. Filter interventions list with `computed`.
**When to use:** When data volume is small enough (20/page) that client-side filtering avoids re-fetching.

```typescript
// Source: app/pages/deputies/[id].vue — mirrors debate thread page pattern
const route = useRoute()
const page = ref(1)
const activeTag = ref<string | null>(null)

const { data, status, error } = await useFetch(`/api/deputies/${route.params.id}`, {
  query: { page },
  watch: [page],
})

// Client-side tag filter on loaded interventions
const filteredInterventions = computed(() => {
  if (!activeTag.value) return data.value?.interventions?.data ?? []
  return (data.value?.interventions?.data ?? []).filter(i =>
    i.tags.some(t => t.slug === activeTag.value)
  )
})
```

**Note:** The active tag filter resets when page changes. This is acceptable UX — filtering is within the current page of interventions.

### Pattern 2: Deputies List Page — useFetch with reactive query params

**What:** List of deputies with search input and group filter dropdown. Mirrors the debates list pattern (index.vue + infinite scroll or simple pagination).
**When to use:** Always for paginated lists.

```typescript
// Source: mirrors app/pages/index.vue pattern
const page = ref(1)
const search = ref('')
const group = ref<string | null>(null)

const allDeputies = ref<any[]>([])

const { data, status } = await useFetch('/api/deputies', {
  query: { page, search, group },
  lazy: true,
  watch: [page, search, group],
})

// Reset list and go back to page 1 when filters change
watch([search, group], () => {
  allDeputies.value = []
  page.value = 1
})

watch(data, (newData) => {
  if (newData?.data) {
    if (page.value === 1) {
      allDeputies.value = newData.data
    } else {
      allDeputies.value.push(...newData.data)
    }
  }
}, { immediate: true })
```

**Critical:** When filters change, reset both `allDeputies` and `page` simultaneously. Failure to reset `allDeputies` causes duplicates; failure to reset `page` means the query doesn't re-fire from page 1.

### Pattern 3: Bidirectional Navigation

**What:** From deputy profile, each intervention links to `/debates/:debateId`. From debate thread, the speaker name/avatar links to `/deputies/:deputyId`.

**Debate thread → Deputy profile (new):** In `InterventionCard`, the speaker name becomes a `NuxtLink` when `deputyId` is present.

```html
<!-- In InterventionCard.vue — add deputyId prop, conditionally link name -->
<NuxtLink
  v-if="deputy && deputyId"
  :to="`/deputies/${deputyId}`"
  class="font-semibold text-sm text-ink hover:text-bronze transition-colors duration-200"
>
  {{ displayName }}
</NuxtLink>
<span v-else class="font-semibold text-sm text-ink">{{ displayName }}</span>
```

**Deputy profile → Debate thread (new):** Each intervention in the profile list shows debate title as a link.

```html
<NuxtLink :to="`/debates/${intervention.debateId}`" class="text-xs text-bronze hover:text-bronze-dark">
  {{ intervention.debate.title }}
</NuxtLink>
```

### Pattern 4: Tag Stats Bar (Deputy Profile Header)

**What:** Visual tag distribution — top N tags displayed as percentage bars or pill list with counts.
**Design constraint:** Marbre & Bronze system — use `bg-bronze`, `bg-bronze-light`, `text-ink-muted`. No shadows.

```html
<!-- Tag stat pills — simple count display -->
<button
  v-for="tag in data.tagStats.slice(0, 8)"
  :key="tag.slug"
  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-marble-dark border border-stone-border hover:border-bronze/40 transition-colors"
  :class="{ 'border-bronze text-bronze': activeTag === tag.slug }"
  @click="activeTag = activeTag === tag.slug ? null : tag.slug"
>
  {{ tag.name }}
  <span class="text-ink-muted">{{ tag.count }}</span>
</button>
```

### Pattern 5: Deputy Card Component

**What:** Card for the deputies list — photo, name, group badge, constituency.
**Mirrors:** `DebateCard.vue` structure (NuxtLink wrapper, `bg-parchment`, `rounded-xl`, `border-stone-border`, hover `border-bronze/40`).

```html
<!-- DeputyCard.vue — follows DebateCard.vue pattern -->
<NuxtLink
  :to="`/deputies/${id}`"
  class="flex items-center gap-3 bg-parchment rounded-xl border border-stone-border p-4 hover:border-bronze/40 transition-colors duration-200"
>
  <img v-if="photoUrl" :src="photoUrl" class="w-12 h-12 rounded-full object-cover border border-stone-border" />
  <div v-else class="w-12 h-12 rounded-full bg-bronze flex items-center justify-center text-white text-sm font-bold">
    {{ initials }}
  </div>
  <div class="flex-1 min-w-0">
    <p class="font-semibold text-ink text-sm">{{ fullName }}</p>
    <p v-if="constituency" class="text-xs text-ink-muted truncate">{{ constituency }}</p>
    <GroupBadge v-if="group" :group="group" class="mt-1" />
  </div>
</NuxtLink>
```

### Anti-Patterns to Avoid

- **Duplicate accumulation on filter change:** When search/group changes on the deputies list, must reset `allDeputies.value = []` before `page.value = 1`. If only page is reset, the watcher fires but `allDeputies` still has old data.
- **Tag filter crossing pages:** Tag filtering is client-side, operating on the current page's interventions only. Don't implement "filter all interventions" — that would require API changes.
- **Adding deputyId prop to InterventionCard from debates API:** The debates API (`/api/debates/:id`) already returns `deputyId` in interventions. No API change needed to enable the profile link — just pass the prop through.
- **N+1 in deputy profile interventions:** Already solved in the API (batch tag fetch with `inArray`). Don't re-implement N+1 queries on the client.
- **`v-html` for intervention content:** Already established (D-0401-02) — use `whitespace-pre-wrap`, never `v-html`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination state management | Custom pagination class | `ref(page)` + `watch: [page]` pattern (already proven in debates list) | Already established, no edge cases |
| Group color resolution | Inline color logic | `getGroupColor()` + `getGroupLabel()` from `app/utils/groupColors.ts` | Already exists, handles all groups + fallback |
| Group badge display | Custom badge HTML | `GroupBadge` component | Already exists |
| Intervention rendering | New card component | `InterventionCard` with added `deputyId` prop | Already proven, add prop only |
| Date formatting | Custom formatter | `new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long', timeZone: 'Europe/Paris' })` | Already established (D-0402-01) |
| Loading state | Custom spinner | `LoadingSpinner` component | Already exists |

**Key insight:** This phase is 90% composition of existing pieces. The API is complete, the design system is defined, components exist. The only net-new code is the profile page layout, deputies list page, and a `DeputyCard` component.

## Common Pitfalls

### Pitfall 1: Filter Reset Race Condition
**What goes wrong:** Search/group filter changes, page resets to 1, but `allDeputies` isn't cleared. First page re-loads and appends to old list, causing duplicates.
**Why it happens:** Two separate `watch` calls — one for filter change (reset list + page), one for data append.
**How to avoid:** In the filter watcher, set `allDeputies.value = []` and `page.value = 1` atomically in the same handler. The data watcher must check `page.value === 1` and replace instead of push.
**Warning signs:** Duplicate deputy names in the list after searching.

### Pitfall 2: InterventionCard deputyId Prop Not Passed
**What goes wrong:** The debate thread page uses `v-bind="intervention"` spread. If the API returns `deputyId` in the intervention object, it auto-passes to `InterventionCard`. But the component must declare the prop or it will silently ignore it.
**Why it happens:** Vue 3 with `v-bind` spread passes all props; only declared props are reactive/accessible.
**How to avoid:** Add `deputyId: number | null` to `InterventionCard` props interface. The debates API already returns `deputyId` — confirm the field name matches.
**Warning signs:** Link to deputy profile is never rendered even when deputy exists.

### Pitfall 3: Tag Filter UX — Active Tag Lost on Pagination
**What goes wrong:** User filters by tag "Budget", clicks "load more" to get next page, active tag filter disappears (interventions are now unfiltered again).
**Why it happens:** Tag filter is client-side on the loaded slice. Pagination loads new data which replaces/appends, but the filter computed is only on the current slice.
**How to avoid:** Accept this limitation explicitly — tag filter is a within-page filter. Document it as such or (acceptable) reset filter when page changes. Don't try to server-side filter by tag (out of scope).
**Warning signs:** Confusing UX when user has tag active + tries to paginate.

### Pitfall 4: Photo URL Broken Images
**What goes wrong:** Deputy photo URLs (from AN official data) may be expired, missing, or CORS-blocked.
**Why it happens:** External image sources are unreliable.
**How to avoid:** Always have an initials fallback (already in `InterventionCard`). Use `@error` handler on `<img>` to swap to fallback, or simply show initials when `photoUrl` is null.
**Warning signs:** Broken image icons in the deputy list/profile.

### Pitfall 5: Navigation — Deputies Nav Link Missing
**What goes wrong:** Header only has "Débats" nav link. After adding `/deputies`, there's no nav entry.
**Why it happens:** Layout nav is static in `default.vue`.
**How to avoid:** Add "Députés" nav link to `app/layouts/default.vue` as part of the first task of this phase.
**Warning signs:** No way to reach the deputies list from the UI.

## Code Examples

Verified patterns from codebase:

### useFetch with reactive page (established in index.vue)
```typescript
// Source: app/pages/index.vue
const page = ref(1)
const { data, status } = await useFetch('/api/debates', {
  query: { page, limit: 20 },
  lazy: true,
  watch: [page],
})
```

### Paginated response shape (from pagination.ts)
```typescript
// Source: server/utils/pagination.ts — response shape for useFetch consumers
{
  data: T[],
  pagination: {
    page: number,
    limit: number,
    total: number,
    totalPages: number,
  }
}
```

### Deputy API response shape (from /api/deputies/:id)
```typescript
// Source: server/api/deputies/[id].get.ts
{
  deputy: {
    id, officialId, firstName, lastName, fullName,
    group, photoUrl, constituency, isActive, createdAt, updatedAt
  },
  interventions: {
    data: Array<{
      id, debateId, deputyId, speakerName, speakerRole,
      content, orderInDebate, createdAt,
      debate: { title: string | null, date: Date | null },
      tags: Array<{ id, name, slug }>
    }>,
    pagination: { page, limit, total, totalPages }
  },
  tagStats: Array<{ name: string, slug: string, count: number }>
}
```

### Intl date formatting (established decision D-0402-01)
```typescript
// Source: app/components/DebateCard.vue
const formattedDate = computed(() => {
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(props.date))
})
```

### Group color + label utils (D-0401-01)
```typescript
// Source: app/utils/groupColors.ts — auto-imported by Nuxt
const color = computed(() => getGroupColor(props.group))  // hex string
const label = computed(() => getGroupLabel(props.group))  // full name
```

### Page validation (established in debates/[id].vue)
```typescript
// Source: app/pages/debates/[id].vue
definePageMeta({
  validate: (route) => {
    return /^\d+$/.test(String(route.params.id))
  },
})
```

### IntersectionObserver infinite scroll (established in index.vue)
```typescript
// Source: app/pages/index.vue
import { useIntersectionObserver } from '@vueuse/core'
const sentinel = useTemplateRef('sentinel')
useIntersectionObserver(
  sentinel,
  ([entry]) => {
    if (entry.isIntersecting && status.value !== 'pending' && hasMore.value) {
      page.value++
    }
  },
  { rootMargin: '200px' },
)
```

## State of the Art

| Old Approach | Current Approach | Status | Impact |
|--------------|------------------|--------|--------|
| Separate API call for tag filter | Client-side computed filter | Phase 5 design | Simpler, no API change needed |
| Hard-coded nav links | Already in default.vue | Existing | Add "Députés" entry |
| Separate InterventionCard for profile | Extend existing with `deputyId` prop | Phase 5 design | Avoid component duplication |

## Open Questions

1. **Tag filter scope — within-page vs. all interventions**
   - What we know: Current API returns paginated interventions (20/page). Tag filter via `?tag=` would require API changes.
   - What's unclear: Is client-side per-page filtering acceptable UX for the MVP?
   - Recommendation: Accept per-page tag filtering for Phase 5. Phase 6 (Recherche & Filtres) can add server-side filtering if needed.

2. **Deputies list — infinite scroll vs. alphabetical pagination**
   - What we know: API returns deputies ordered by `lastName ASC`. Deputies list could be 500+ entries.
   - What's unclear: User preference for navigation (A-Z jump vs. scroll).
   - Recommendation: Use infinite scroll (same pattern as debates list) for simplicity. A-Z navigation is a Phase 7 polish item.

3. **InterventionCard — backlink from debate thread to deputy profile**
   - What we know: The API `/api/debates/:id` returns `deputyId` in each intervention. `InterventionCard` currently accepts a `deputy` object but no `deputyId`.
   - What's unclear: Should clicking the deputy name navigate to profile, or open a popover?
   - Recommendation: Simple `NuxtLink` on the name when `deputyId` is non-null. No popover — that's Phase 7 polish.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `server/api/deputies/[id].get.ts` — exact API response shape
- Direct codebase inspection — `server/api/deputies/index.get.ts` — list API with search/group filter
- Direct codebase inspection — `app/pages/index.vue` — infinite scroll + useFetch pattern
- Direct codebase inspection — `app/pages/debates/[id].vue` — page structure, validate, useFetch
- Direct codebase inspection — `app/components/InterventionCard.vue` — existing props interface
- Direct codebase inspection — `app/components/DebateCard.vue` — card pattern to replicate
- Direct codebase inspection — `app/utils/groupColors.ts` — group color/label utils
- Direct codebase inspection — `app/layouts/default.vue` — nav structure
- Direct codebase inspection — `app/assets/css/main.css` — Marbre & Bronze design tokens

### Secondary (MEDIUM confidence)
- Phase 4 RESEARCH.md — confirmed established patterns and decisions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed, codebase fully read
- Architecture: HIGH — exact API shape known, page pattern proven in phase 4, patterns derive directly from existing code
- Pitfalls: HIGH — derive from concrete code analysis (prop interfaces, watch patterns, API shapes)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable stack, no fast-moving dependencies)
