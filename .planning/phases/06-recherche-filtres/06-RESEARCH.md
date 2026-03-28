# Phase 6: Recherche & Filtres - Research

**Researched:** 2026-03-28
**Domain:** Nuxt 4 search UI, PostgreSQL FTS integration, URL-synced filter state
**Confidence:** HIGH

## Summary

Phase 6 is almost entirely UI work. The backend search engine is already fully built: `GET /api/search` supports full-text search with French-language FTS (GIN index on `to_tsvector('french', content)`), `websearch_to_tsquery`, `ts_rank` ordering, `ts_headline` highlighting with `<mark>` tags, plus optional filters `deputyId`, `debateId`, and `tag`. The backend returns paginated results with `data[]`, `pagination` (page/limit/total/totalPages), and each result has `rank`, `highlight` (HTML with `<mark>`), `debate` object, and `deputy` object.

The frontend needs: (1) a global search bar in the header or as a prominent page element, (2) a `/search` results page with contextual excerpts, filter controls, and pagination, (3) URL-synced filter state so searches are linkable/bookmarkable. The existing infinite scroll pattern (`useIntersectionObserver` from `@vueuse/core`) is appropriate here but requires a filter-reset guard — identical to the pattern already used in `/deputies`. The highlight HTML from the backend contains raw `<mark>` tags that must be rendered with `v-html` (not text interpolation), which is safe since content comes from our own FTS, not user input.

The key design decision for this phase is URL state management: using `useRoute` + `useRouter` to sync query params (`q`, `deputyId`, `tag`) into the URL. This makes searches shareable and supports browser back/forward correctly. Nuxt 4 provides `useRoute().query` and `navigateTo()` / `useRouter().push()` for this purpose. No extra library is needed.

**Primary recommendation:** Build `/search` page with URL-synced state (`q`, `deputyId`, `tag` as query params), render highlights with `v-html`, add search link to header nav, reuse existing infinite scroll + filter-reset pattern. Zero new dependencies required.

## Prior Decisions (from phase context)

These decisions are locked — do not explore alternatives:

- **D-0303-01**: Use `db.execute(sql\`...\`)` for FTS queries — Drizzle query builder cannot express `ts_rank`/`ts_headline`/optional WHERE fragments cleanly. Already implemented in `server/api/search.get.ts`.
- **D-0303-02**: `websearch_to_tsquery` over `to_tsquery` — handles unescaped user input safely. Already implemented.
- **D-0302-01**: `tagStats` uses separate GROUP BY query, not in-memory. Already implemented on deputy profile.

## Standard Stack

### Core (all already installed — zero new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nuxt | ^4.4.2 | File-based routing, `useRoute`/`useRouter`, auto-imports | Already in project |
| vue | ^3.5.30 | Composition API, `ref`, `computed`, `watch` | Already in project |
| @vueuse/core | ^14.2.1 | `useIntersectionObserver` for infinite scroll | Already installed |
| tailwindcss | ^4.2.2 | Marbre & Bronze design tokens | Already in project |

### No new installations needed

All required functionality (routing, reactive state, search input debouncing via `watch`, HTTP fetching via `useFetch`) is covered by existing Nuxt 4 + Vue 3 + @vueuse/core stack.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| URL query params via `useRoute`/`useRouter` | `useState` (Nuxt global state) | URL params make searches shareable/bookmarkable — correct choice for a search page |
| `v-html` for highlights | Custom mark component | `v-html` is the right tool; no XSS risk since highlight comes from our own PostgreSQL FTS |
| Infinite scroll for results | Numbered pagination | Infinite scroll is established pattern in this codebase; consistent UX |
| Client-side deputy filter (fetching all deputies) | Server-side filter via `deputyId` | The API already supports `deputyId` filter — use it; no reason to pre-load all deputies |

## Architecture Patterns

### File additions for this phase

```
app/
├── pages/
│   └── search.vue               # Search results page (new)
├── components/
│   └── SearchResultCard.vue     # Result card with highlight, debate/deputy context (new)
├── layouts/
│   └── default.vue              # Add search bar to header (modify existing)
```

### Pattern 1: URL-Synced Filter State

**What:** Search query and filters live in URL query params. The page reads initial state from `useRoute().query` on mount, and writes state back to URL on change via `useRouter().replace()`. This enables shareable URLs and correct browser history.

**When to use:** Any page where filters should be bookmarkable or linkable.

**Example:**
```typescript
// Source: Nuxt 4 docs — https://nuxt.com/docs/api/composables/use-route
const route = useRoute()
const router = useRouter()

const q = ref((route.query.q as string) ?? '')
const activeTag = ref((route.query.tag as string) ?? '')
const deputyId = ref(route.query.deputyId ? Number(route.query.deputyId) : null)

// Sync state back to URL on every filter change
watch([q, activeTag, deputyId], () => {
  router.replace({
    query: {
      ...(q.value ? { q: q.value } : {}),
      ...(activeTag.value ? { tag: activeTag.value } : {}),
      ...(deputyId.value ? { deputyId: String(deputyId.value) } : {}),
    },
  })
  // Reset accumulator and page
  allResults.value = []
  page.value = 1
})
```

### Pattern 2: Rendering FTS Highlights Safely

**What:** The API's `ts_headline` returns HTML like `This is about <mark>immigration</mark> in France`. Must be rendered with `v-html`, not `{{ }}`.

**When to use:** Anywhere `highlight` from the search API is displayed.

**Example:**
```vue
<!-- Source: observed in server/api/search.get.ts — ts_headline output contains <mark> tags -->
<p class="text-sm text-ink/85 leading-relaxed" v-html="result.highlight" />
```

The `<mark>` tag must be styled in CSS — add to `main.css`:
```css
/* FTS highlight marks */
mark {
  background-color: var(--color-bronze-light);
  color: var(--color-ink);
  border-radius: 2px;
  padding: 0 2px;
}
```

### Pattern 3: Filter Reset on Query Change (established codebase pattern)

**What:** When search query or filters change, reset the accumulator and page before fetching. This prevents stale results from appearing.

**When to use:** Every time a filter value changes on a page using the infinite scroll + accumulator pattern.

**Example (from existing `/deputies/index.vue`):**
```typescript
// Source: app/pages/deputies/index.vue
watch([search, group], () => {
  allDeputies.value = []
  page.value = 1
})
```
Apply the same pattern for `[q, activeTag, deputyId]` on the search page.

### Pattern 4: Search Input with Debounce

**What:** Don't fire a new API call on every keystroke. Use `watchDebounced` from `@vueuse/core` (already installed) or `watch` with a manual debounce. Recommended: `watchDebounced` with 300ms delay.

**When to use:** Any text input that triggers API calls.

**Example:**
```typescript
// Source: @vueuse/core docs — watchDebounced
import { watchDebounced } from '@vueuse/core'

const inputValue = ref('')  // raw input, not URL-synced
const q = ref('')           // debounced value, URL-synced

watchDebounced(inputValue, (val) => {
  q.value = val
}, { debounce: 300 })
```

### Anti-Patterns to Avoid

- **Rendering `highlight` without `v-html`:** `{{ result.highlight }}` will display raw HTML as text. The `<mark>` tags become visible characters. Always use `v-html` for this field.
- **Not resetting accumulator on filter change:** Causes stale results from previous query to appear mixed with new results. The existing codebase already guards against this in `/deputies` — replicate exactly.
- **Firing search without a query:** The API returns 400 when `q` is empty. Guard with `if (!q.value.trim()) return` before fetching.
- **Two-way binding URL params directly:** Don't do `v-model` on `route.query.q`. Use a local `ref` and sync to URL in a `watch`. Direct mutation of route query causes Vue Router warnings.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounced input | Custom setTimeout/clearTimeout | `watchDebounced` from @vueuse/core | Already in project, handles cleanup automatically |
| Text highlighting | Custom regex replace | `ts_headline` output from existing API | Backend already does it with correct French stemming |
| Infinite scroll | Manual scroll event listener | `useIntersectionObserver` from @vueuse/core | Established pattern in this codebase (`/deputies`, `/`) |
| French FTS | Custom full-text search | PostgreSQL `to_tsvector('french', ...)` | Already implemented with GIN index in schema |
| Input sanitization for FTS | Manual escaping | `websearch_to_tsquery` | Already chosen (D-0303-02); handles user input safely |

**Key insight:** The backend is complete. Every "feature" of the search is already implemented server-side. The phase is a UI integration task, not a search engineering task.

## Common Pitfalls

### Pitfall 1: `v-html` XSS — misunderstanding the risk level
**What goes wrong:** Developer avoids `v-html` out of XSS caution and renders `{{ result.highlight }}`, seeing raw HTML tags in the UI.
**Why it happens:** General `v-html` XSS guidance is correct in general, but doesn't apply when the content source is your own controlled backend.
**How to avoid:** Use `v-html` for `result.highlight`. The content is generated by PostgreSQL's `ts_headline` from your own database — not from user input reflected directly. User's search query goes through `websearch_to_tsquery` on the server, not into the highlight output verbatim.
**Warning signs:** `<mark>` appearing as literal text in the rendered output.

### Pitfall 2: Missing `<mark>` styles
**What goes wrong:** Highlights render but are invisible because `<mark>` has default browser styling (yellow), or no styling at all in Tailwind CSS v4's reset.
**Why it happens:** Tailwind's preflight/reset normalizes browser defaults. `<mark>` may not have expected styling.
**How to avoid:** Explicitly style `mark { }` in `main.css` using the design system tokens (`bronze-light` background).
**Warning signs:** Text looks unstyled, or yellow highlight appears that clashes with the Marbre & Bronze palette.

### Pitfall 3: Stale results after filter change
**What goes wrong:** User searches "immigration", gets 30 results. Changes tag filter. Old "immigration" results appear briefly or remain mixed with new filtered results.
**Why it happens:** The infinite scroll accumulator (`allResults.value.push(...)`) appends without resetting. When filters change, `page` must reset to 1 AND the accumulator must be cleared.
**How to avoid:** `watch([q, activeTag, deputyId], () => { allResults.value = []; page.value = 1 })` — identical to the existing pattern in `/deputies/index.vue`.
**Warning signs:** Duplicate results appearing, or result count not matching `pagination.total`.

### Pitfall 4: Empty query API call
**What goes wrong:** On initial page load with no `?q=` param, the page tries to fetch `/api/search` without a query, gets a 400 error, and shows an error state.
**Why it happens:** `useFetch` triggers automatically. If `q` is empty, the API returns `400: Missing required query parameter: q`.
**How to avoid:** Guard the fetch with a `computed` condition or `immediate: false` with a manual trigger. The simplest approach: skip `useFetch` when `q` is empty, show a "type to search" placeholder instead.
**Warning signs:** 400 error in the network tab on initial load of `/search`.

### Pitfall 5: `useRoute().query` values are always strings
**What goes wrong:** `route.query.deputyId` is the string `"42"`, not the number `42`. Passing it directly to `useFetch` query causes a type mismatch or unexpected filter behavior.
**Why it happens:** URL query params are always strings in the browser.
**How to avoid:** Parse on read: `const deputyId = route.query.deputyId ? Number(route.query.deputyId) : null`. Already done this way in `server/api/search.get.ts` server-side — do the same client-side.

### Pitfall 6: Double trigger from URL sync + watch
**What goes wrong:** Syncing state to URL triggers the route watcher, which triggers the state watcher, causing an infinite loop of filter resets.
**Why it happens:** `watch` on `route.query` and `watch` on local refs both fire.
**How to avoid:** Do NOT watch `route.query` reactively in a second watcher. Initialize from `route.query` once (on mount), then write back via `router.replace()` without watching the route again. One direction: local ref → URL, never URL → local ref after init.

## Code Examples

Verified patterns from codebase inspection:

### Complete search page structure
```typescript
// app/pages/search.vue
// Source: pattern derived from app/pages/deputies/index.vue
import { watchDebounced, useIntersectionObserver } from '@vueuse/core'

const route = useRoute()
const router = useRouter()

// Initialize from URL params
const inputValue = ref((route.query.q as string) ?? '')
const q = ref((route.query.q as string) ?? '')
const activeTag = ref((route.query.tag as string) ?? '')
const deputyId = ref(route.query.deputyId ? Number(route.query.deputyId) : null)

// Debounce raw input → q
watchDebounced(inputValue, (val) => { q.value = val }, { debounce: 300 })

// Pagination and accumulator
const page = ref(1)
const allResults = ref<any[]>([])
const sentinel = useTemplateRef('sentinel')

// Reset on filter change
watch([q, activeTag, deputyId], () => {
  allResults.value = []
  page.value = 1
  // Sync URL
  router.replace({
    query: {
      ...(q.value ? { q: q.value } : {}),
      ...(activeTag.value ? { tag: activeTag.value } : {}),
      ...(deputyId.value ? { deputyId: String(deputyId.value) } : {}),
    },
  })
})

// Fetch only when q is non-empty
const shouldFetch = computed(() => q.value.trim().length > 0)

const { data, status } = useFetch('/api/search', {
  query: computed(() => ({
    q: q.value,
    page: page.value,
    limit: 20,
    ...(activeTag.value ? { tag: activeTag.value } : {}),
    ...(deputyId.value ? { deputyId: deputyId.value } : {}),
  })),
  immediate: false,         // Don't auto-fetch on empty q
  watch: false,             // Manage manually below
})

// Manual trigger when shouldFetch is true and page/filters change
watch([shouldFetch, page], ([sf]) => {
  if (sf) data.refresh?.()
})

// Append results
watch(data, (newData) => {
  if (!newData?.data) return
  if (page.value === 1) allResults.value = newData.data
  else allResults.value.push(...newData.data)
}, { immediate: true })

const hasMore = computed(() => {
  if (!data.value?.pagination) return false
  return page.value < data.value.pagination.totalPages
})

// Infinite scroll
useIntersectionObserver(sentinel, ([entry]) => {
  if (entry?.isIntersecting && status.value !== 'pending' && hasMore.value) {
    page.value++
  }
}, { rootMargin: '200px' })
```

### Highlight rendering with correct styling
```vue
<!-- Source: pattern derived from server/api/search.get.ts ts_headline output format -->
<!-- In SearchResultCard.vue -->
<p class="text-sm text-ink/85 leading-relaxed search-highlight" v-html="highlight" />
```
```css
/* In app/assets/css/main.css */
/* FTS search highlights — ts_headline produces <mark> tags */
mark {
  background-color: var(--color-bronze-light);
  color: var(--color-ink);
  border-radius: 2px;
  padding: 0 2px;
  font-style: normal;
}
```

### SearchResultCard props contract
```typescript
// Derived from server/api/search.get.ts return shape
interface SearchResult {
  id: number
  speakerName: string
  speakerRole: string | null
  orderInDebate: number
  rank: number
  highlight: string           // HTML from ts_headline — render with v-html
  debate: {
    id: number
    title: string
    date: string
  }
  deputy: {
    id: number
    fullName: string | null
    group: string | null
    photoUrl: string | null
  } | null
}
```

### Header search bar integration
```vue
<!-- In app/layouts/default.vue — modify nav section -->
<!-- Source: existing default.vue pattern -->
<form @submit.prevent="navigateTo({ path: '/search', query: { q: headerSearch } })">
  <input
    v-model="headerSearch"
    type="search"
    placeholder="Rechercher..."
    class="bg-parchment border border-stone-border rounded-lg px-3 py-1.5 text-sm text-ink placeholder:text-ink-muted/60 focus:outline-none focus:border-bronze/40 transition-colors duration-200 w-48"
  />
</form>
```

## API Shape Reference

The existing `GET /api/search` endpoint (fully implemented):

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | string | YES | Search query (passed to `websearch_to_tsquery`) |
| `page` | number | no | Default 1 |
| `limit` | number | no | Default 20, max 100 |
| `deputyId` | number | no | Filter by deputy |
| `debateId` | number | no | Filter by debate |
| `tag` | string | no | Filter by tag slug |

Response shape (from `paginatedResponse` utility):
```typescript
{
  data: SearchResult[],
  pagination: {
    page: number,
    limit: number,
    total: number,
    totalPages: number
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side text search (filter array) | PostgreSQL FTS with GIN index | Phase 3 (already done) | Handles thousands of interventions without sending all data to client |
| Manual `setTimeout` debounce | `watchDebounced` from @vueuse/core | @vueuse available since Phase 5 | Less boilerplate, auto-cleanup |
| Reload page on filter change | `router.replace()` without page reload | Standard Nuxt 4 SPA pattern | Instant filter updates, shareable URLs |

## Open Questions

1. **Tag filter source on search page**
   - What we know: The API supports `?tag=` filter. Tag slugs exist in the DB.
   - What's unclear: Should the search page show a list of available tags to pick from? Or let user type a tag name? No endpoint exists to list all tags.
   - Recommendation: For Phase 6 scope, display tags found in search results (not a pre-loaded tag list). When a result shows a tag pill, clicking it activates the tag filter. This requires zero new API endpoints and is consistent with the deputy profile tag filter UX.

2. **Date range filter**
   - What we know: Phase description mentions "date" as a filter. The API does NOT currently support `dateFrom`/`dateTo` params.
   - What's unclear: Is date filtering expected to be in Phase 6, or was it aspirational in the roadmap?
   - Recommendation: The existing API has no date filter support. Adding it requires a backend change (add `dateFrom`/`dateTo` params to `search.get.ts`). Plan as a task: either implement or explicitly defer. The `debates.date` column exists and is indexed. Implementation would add two optional SQL fragments to the existing FTS query — straightforward given D-0303-01 pattern.

3. **Global header search bar scope**
   - What we know: Phase mentions "barre de recherche globale".
   - What's unclear: Does "global" mean it's in the header on all pages, or just prominent on the `/search` page?
   - Recommendation: Add a compact search input to the header that navigates to `/search?q=...` on submit. The actual search results live on `/search`. This is the standard pattern (Google-style: header input → dedicated results page).

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `server/api/search.get.ts` — full API implementation verified
- Codebase inspection: `server/db/schema.ts` — FTS GIN index confirmed on interventions
- Codebase inspection: `app/pages/deputies/index.vue` — infinite scroll + filter reset pattern
- Codebase inspection: `app/assets/css/main.css` — Marbre & Bronze design tokens
- Codebase inspection: `app/layouts/default.vue` — header structure
- Codebase inspection: `package.json` — installed versions confirmed

### Secondary (MEDIUM confidence)
- Nuxt 4 routing docs (useRoute/useRouter/navigateTo): standard composables, well-documented
- @vueuse/core watchDebounced: confirmed available in ^14.2.1

### Tertiary (LOW confidence)
- None — all claims grounded in codebase inspection or well-known APIs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from package.json and codebase
- Architecture: HIGH — derived from existing patterns in the same codebase
- API contract: HIGH — read directly from server/api/search.get.ts
- Pitfalls: HIGH — derived from codebase patterns + known Vue/Nuxt behaviors
- Date filter question: LOW — unclear if required in scope (no backend implementation exists yet)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable stack, 30 days)
