# Phase 4: UI Debats (Thread View) - Research

**Researched:** 2026-03-27
**Domain:** Nuxt 4 UI, Tailwind CSS v4, Vue 3 composables, infinite scroll
**Confidence:** HIGH

## Summary

Phase 4 builds the user-facing UI on top of the already-complete API layer. The stack is fully defined by the project: Nuxt 4 with the `app/` directory structure, Tailwind CSS v4 (CSS-first config via `@theme`), and Vue 3 Composition API. No additional UI framework is needed — the existing setup is sufficient to build a Twitter-style thread view.

The two key technical patterns are: (1) `useFetch` with reactive `query` ref for the debates list page with pagination, and (2) `useIntersectionObserver` from `@vueuse/core` for infinite scroll on the debate thread page. Both patterns are well-documented and fit naturally into Nuxt 4's auto-import system. The main risks are hydration mismatches from SSR and layout shifts during image/avatar loading.

The component hierarchy is straightforward: a dumb `InterventionCard` component (avatar, name, group badge, content text) composed in a scrollable list, with a sentinel element at the bottom triggering the next page load. Tailwind v4 already in the project handles all styling — no additional CSS framework needed.

**Primary recommendation:** Build with `useFetch` + reactive page ref for list, `@vueuse/core` `useIntersectionObserver` for infinite scroll on thread page. No UI component library — hand-build the thread components with Tailwind.

## Standard Stack

### Core (already in project — no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nuxt | ^4.4.2 | Framework, routing, SSR, auto-imports | Already installed |
| vue | ^3.5.30 | Reactivity, composables, SFCs | Already installed |
| tailwindcss | ^4.2.2 | Utility-first CSS via `@tailwindcss/vite` | Already installed, v4 CSS-first |
| vue-router | ^5.0.4 | File-based routing (`pages/`) | Already installed |

### Supporting (new install required)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @vueuse/core | ^12.x | `useIntersectionObserver` composable | Infinite scroll sentinel detection |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @vueuse/core | Native IntersectionObserver | VueUse wraps cleanup, reactive integration — saves ~30 lines of boilerplate |
| Hand-built thread cards | Nuxt UI / PrimeVue | Overkill for this phase; adds bundle weight; @theme colors already defined |
| Client-side infinite scroll | Server-side cursor pagination | Client-side is simpler for this scale; cursor pagination is a future optimization |

**Installation:**
```bash
npm install @vueuse/core
```

## Architecture Patterns

### Recommended Project Structure

All new files go under `app/` — Nuxt 4 auto-imports everything from `app/components/`, `app/composables/`, `app/utils/`.

```
app/
├── pages/
│   ├── index.vue              # Debates list (home page)
│   └── debates/
│       └── [id].vue           # Debate thread view (dynamic route)
├── components/
│   ├── DebateCard.vue         # Card in the list (title, date, session type)
│   ├── InterventionCard.vue   # Single thread post (avatar, name, group, content)
│   ├── GroupBadge.vue         # Political group color badge
│   └── LoadingSpinner.vue     # Shared loading state
└── composables/
    └── useDebateThread.ts     # Encapsulates infinite-scroll logic for debate page
```

### Pattern 1: Paginated List with useFetch

For the home page debates list, `useFetch` with a reactive `query` object handles pagination. Changing `page.value` automatically triggers a new fetch.

**What:** Reactive query params auto-watched by `useFetch`
**When to use:** Initial data load + page-by-page navigation (load more button or scroll)

```typescript
// Source: https://nuxt.com/docs/4.x/getting-started/data-fetching
// app/pages/index.vue
const page = ref(1)
const allDebates = ref<Debate[]>([])

const { data, status } = await useFetch('/api/debates', {
  query: { page, limit: 20 },
  watch: [page],
  // Important: lazy:true so navigation doesn't block
  lazy: true,
})

// Append results for infinite scroll
watch(data, (newData) => {
  if (newData?.data) {
    allDebates.value.push(...newData.data)
  }
})
```

### Pattern 2: Infinite Scroll with useIntersectionObserver

Place an invisible sentinel `<div>` after the last item. When it enters the viewport, load the next page. Clean up the observer on unmount automatically (VueUse handles this).

**What:** Browser-native IntersectionObserver wrapped in a reactive composable
**When to use:** Debate thread page — potentially hundreds of interventions

```typescript
// Source: https://vueuse.org/core/useintersectionobserver/
// app/composables/useDebateThread.ts
import { useIntersectionObserver } from '@vueuse/core'

export function useDebateThread(debateId: number) {
  const interventions = ref<Intervention[]>([])
  const page = ref(1)
  const hasMore = ref(true)
  const isLoading = ref(false)
  const sentinel = useTemplateRef<HTMLElement>('sentinel')

  async function loadMore() {
    if (isLoading.value || !hasMore.value) return
    isLoading.value = true

    const data = await $fetch(`/api/debates/${debateId}`, {
      query: { page: page.value, limit: 30 }
    })

    interventions.value.push(...data.interventions)
    hasMore.value = page.value < data.pagination.totalPages
    page.value++
    isLoading.value = false
  }

  useIntersectionObserver(
    sentinel,
    ([entry]) => {
      if (entry?.isIntersecting) loadMore()
    },
    { rootMargin: '200px' } // Pre-load 200px before sentinel enters view
  )

  return { interventions, isLoading, hasMore, sentinel, loadMore }
}
```

**Note:** The current debate detail API (`/api/debates/[id].get.ts`) returns ALL interventions in one call — no pagination. For the thread view, this is acceptable if debate sizes are reasonable. If debates have 500+ interventions, the API needs a `page`/`limit` param added. Check data volume first.

### Pattern 3: Dynamic Route for Debate Thread

```
app/pages/debates/[id].vue  →  route: /debates/123
```

```vue
<!-- Source: https://nuxt.com/docs/4.x/directory-structure/app/pages -->
<script setup lang="ts">
const route = useRoute()
const id = Number(route.params.id)

// Validate route param
definePageMeta({
  validate: async (route) => {
    return /^\d+$/.test(String(route.params.id))
  }
})
</script>
```

### Pattern 4: Tailwind v4 Component Styling

The project uses `@tailwindcss/vite` and CSS-first config. Custom colors `--color-primary` and `--color-accent` are defined in `app/assets/css/main.css` via `@theme`. These become Tailwind utilities: `text-primary`, `bg-primary`, `text-accent`, `bg-accent`.

For group badges, define group colors in the `@theme` block or use inline CSS variables:

```css
/* app/assets/css/main.css */
@import "tailwindcss";

@theme {
  --color-primary: #1a365d;
  --color-accent: #e53e3e;
  /* Political group colors */
  --color-group-lfi: #e63946;
  --color-group-ens: #f4a261;
  --color-group-rn: #2a6496;
}
```

In components, use `bg-[var(--color-group-lfi)]` or add dedicated utilities via `@theme`.

### Anti-Patterns to Avoid

- **Fetching all interventions client-side on large debates:** The current API returns all at once. If a debate has 300+ interventions, this is a 300-row query with joins. Add pagination to the API if needed, don't try to paginate client-side from a full dataset.
- **Watching page ref without deduplication guard:** If the sentinel fires twice before `isLoading` is set, you get duplicate requests. Always guard with `if (isLoading.value) return`.
- **Using `<img>` directly for deputy photos without fallback:** `photoUrl` can be null (non-deputy speakers). Always use a conditional with an initials fallback.
- **Calling `useFetch` outside `<script setup>`:** Nuxt composables must be called in setup context. Moving fetch logic to a composable is fine as long as the composable is called from setup.
- **`bg-gradient-*` syntax from Tailwind v3:** In v4 it is `bg-linear-*`. Don't use the old gradient class names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sentinel visibility detection | Custom scroll event listener + position math | `useIntersectionObserver` (@vueuse/core) | Race conditions, performance, cleanup leaks |
| HTTP fetch with SSR deduplication | `$fetch` wrapped in `onMounted` | `useFetch` | SSR hydration, deduplication, automatic caching |
| Reactive query string construction | Manual URL string concatenation | `useFetch` `query` option with refs | Auto-serializes, auto-watches, type-safe |
| Image with fallback + loading state | `<img @error>` with manual state | Conditional template with computed initials | Simple enough to hand-build, but don't forget the null check |

**Key insight:** The Nuxt data fetching composables handle SSR hydration, request deduplication, and caching automatically. Using `$fetch` directly in `onMounted` bypasses all of this and causes data to flash on client hydration.

## Common Pitfalls

### Pitfall 1: Infinite Scroll Double-Trigger Race Condition
**What goes wrong:** The sentinel fires the IntersectionObserver callback twice in quick succession (on mount + on first scroll). `loadMore()` is called twice, page 2 is loaded twice.
**Why it happens:** Observer fires immediately if sentinel is already in viewport when component mounts.
**How to avoid:** Guard with `isLoading.value` check at the top of `loadMore()`. Set it to `true` synchronously before any await.
**Warning signs:** Duplicate interventions appearing in the thread.

### Pitfall 2: SSR Hydration Mismatch with Dynamic Dates
**What goes wrong:** `debate.date` is a timestamp. Formatting it server-side and client-side with `new Date().toLocaleDateString()` can produce different strings (locale/timezone differences), causing a Vue hydration warning.
**Why it happens:** Server locale may differ from browser locale.
**How to avoid:** Use a consistent date formatting util (e.g., `Intl.DateTimeFormat` with explicit `locale: 'fr-FR'` and `timeZone: 'Europe/Paris'`), or format dates client-side only using `v-if="!pending"` pattern.
**Warning signs:** Console warning "Hydration text mismatch".

### Pitfall 3: Null deputy on Non-Deputy Speakers
**What goes wrong:** Interventions can have `deputy: null` (ministers, president of session, etc.) — `speakerRole` is set but `deputyId` is null. Accessing `intervention.deputy.fullName` crashes.
**Why it happens:** Schema allows `deputyId` to be null. API returns `deputy: null` in this case.
**How to avoid:** Always use optional chaining: `intervention.deputy?.fullName ?? intervention.speakerName`.
**Warning signs:** Runtime error "Cannot read properties of null (reading 'fullName')".

### Pitfall 4: Tailwind v4 `@theme` Variable Scope
**What goes wrong:** Adding a CSS variable with `--color-*` in a component's `<style>` block doesn't create Tailwind utilities. Only variables in the `@theme` block in the main CSS file generate utilities.
**Why it happens:** Tailwind v4 scans only the `@theme` directive for utility generation.
**How to avoid:** Add all custom color/spacing tokens to `app/assets/css/main.css` inside `@theme { }`. For one-off values, use arbitrary syntax: `bg-[#e63946]`.
**Warning signs:** Custom utility class not applying, class present in HTML but no CSS generated.

### Pitfall 5: useFetch Key Collision
**What goes wrong:** Two `useFetch('/api/debates', ...)` calls with different `query` params but the same key get deduplicated — second call returns cached data from first.
**Why it happens:** `useFetch` auto-generates a key from the URL. If query params are reactive, the key updates. If you call `useFetch` twice with the same static URL, they share state.
**How to avoid:** Either use reactive query params (auto-generates unique keys per request) or pass an explicit `key` option.
**Warning signs:** Wrong page of results appearing.

## Code Examples

### InterventionCard Component Structure
```vue
<!-- app/components/InterventionCard.vue -->
<!-- Source: based on API shape from server/api/debates/[id].get.ts -->
<script setup lang="ts">
interface Props {
  speakerName: string
  speakerRole: string | null
  content: string
  orderInDebate: number
  deputy: {
    fullName: string
    group: string | null
    photoUrl: string | null
  } | null
  tags: { id: number; name: string; slug: string }[]
}

const props = defineProps<Props>()

// Deputy can be null for non-elected speakers (ministers, president)
const displayName = computed(() =>
  props.deputy?.fullName ?? props.speakerName
)
const initials = computed(() =>
  displayName.value.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
)
</script>

<template>
  <article class="flex gap-3 py-4 border-b border-gray-100">
    <!-- Avatar -->
    <div class="flex-shrink-0 w-10 h-10">
      <img
        v-if="deputy?.photoUrl"
        :src="deputy.photoUrl"
        :alt="displayName"
        class="w-10 h-10 rounded-full object-cover"
      />
      <div
        v-else
        class="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center text-sm font-bold"
      >
        {{ initials }}
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="font-semibold text-sm">{{ displayName }}</span>
        <GroupBadge v-if="deputy?.group" :group="deputy.group" />
        <span v-if="speakerRole" class="text-xs text-gray-500">{{ speakerRole }}</span>
      </div>
      <p class="mt-1 text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
        {{ content }}
      </p>
    </div>
  </article>
</template>
```

### Infinite Scroll Sentinel Pattern in Template
```vue
<!-- app/pages/debates/[id].vue -->
<template>
  <div>
    <InterventionCard
      v-for="intervention in interventions"
      :key="intervention.id"
      v-bind="intervention"
    />

    <!-- Sentinel: triggers loadMore when it enters viewport -->
    <div ref="sentinel" class="h-4" />

    <div v-if="isLoading" class="py-4 text-center text-gray-400 text-sm">
      Chargement...
    </div>
    <div v-if="!hasMore && interventions.length > 0" class="py-4 text-center text-gray-400 text-sm">
      Fin du debat
    </div>
  </div>
</template>
```

### Debates List Page with Load More
```vue
<!-- app/pages/index.vue -->
<script setup lang="ts">
const page = ref(1)
const allDebates = ref<any[]>([])

const { data, status } = await useFetch('/api/debates', {
  query: { page, limit: 20 },
  lazy: true,
  watch: [page],
})

watch(data, (newData) => {
  if (newData?.data) {
    allDebates.value.push(...newData.data)
  }
}, { immediate: true })

const hasMore = computed(() =>
  data.value ? page.value < data.value.pagination.totalPages : false
)

function loadMore() {
  if (status.value !== 'pending') page.value++
}
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tailwind.config.js` | `@theme {}` block in CSS | Tailwind v4 (Jan 2025) | No JS config file; all project tokens in CSS |
| `@tailwind base/components/utilities` | `@import "tailwindcss"` | Tailwind v4 (Jan 2025) | Single import line |
| `bg-gradient-to-r` | `bg-linear-to-r` | Tailwind v4 | Name change; old class silently does nothing |
| `nuxt.config.js` content array | Automatic content detection | Tailwind v4 Vite plugin | No content config needed |
| Custom IntersectionObserver setup | `useIntersectionObserver` from @vueuse/core | VueUse v10+ | Handles cleanup, reactive options, TypeScript |

**Deprecated/outdated:**
- `@tailwind base` / `@tailwind components` / `@tailwind utilities` directives: replaced by `@import "tailwindcss"` in v4.
- `tailwind.config.js` with `theme.extend`: all customization moves to `@theme {}` in the main CSS file.

## Open Questions

1. **Debate size — do we need API-level pagination for interventions?**
   - What we know: Current `/api/debates/[id]` returns ALL interventions in one query. Schema has `orderInDebate` int. A typical séance can have 50-300 interventions.
   - What's unclear: The actual max row count in the ingested data. If a full debate session has 500+ interventions with content, a single 500-row join query may be slow.
   - Recommendation: Build the UI assuming the current API is sufficient. After first data load test, if response time > 500ms or payload > 1MB, add `page`/`limit` query params to `/api/debates/[id]`.

2. **Political group color mapping**
   - What we know: `deputy.group` is a free-text string from the AN data (e.g., "Rassemblement National", "La France insoumise"). Values are not normalized to an enum.
   - What's unclear: Exact string values in the ingested data.
   - Recommendation: Build `GroupBadge.vue` with a `groupColorMap` record mapping known group strings to Tailwind colors. Add a fallback `bg-gray-200` for unknown groups. Check actual group strings via `SELECT DISTINCT political_group FROM deputies` after ingestion.

3. **Deputy photo availability**
   - What we know: `photoUrl` is nullable. AN API provides photo URLs for elected deputies. Non-deputy speakers (ministers, president) always have null.
   - What's unclear: Whether photo URLs from the AN API are stable long-term CDN URLs or session-specific.
   - Recommendation: Always implement fallback initials avatar. Don't block on photo availability.

## Sources

### Primary (HIGH confidence)
- [Nuxt 4 Data Fetching Docs](https://nuxt.com/docs/4.x/getting-started/data-fetching) — useFetch, useAsyncData, watch, lazy, query options
- [Nuxt 4 Pages Docs](https://nuxt.com/docs/4.x/directory-structure/app/pages) — dynamic routes `[id].vue`, definePageMeta, useRoute
- [Nuxt 4 Auto-imports Docs](https://nuxt.com/docs/4.x/guide/concepts/auto-imports) — what gets auto-imported, gotchas
- [Tailwind CSS v4 Blog Post](https://tailwindcss.com/blog/tailwindcss-v4) — breaking changes, @theme, renamed utilities, container queries
- [VueUse useIntersectionObserver](https://vueuse.org/core/useintersectionobserver/) — API, usage, options
- Project source files read directly: `nuxt.config.ts`, `package.json`, `server/db/schema.ts`, `server/api/debates/[id].get.ts`, `app/assets/css/main.css`, `app/layouts/default.vue`

### Secondary (MEDIUM confidence)
- [Nuxt 4 useFetch API Reference](https://nuxt.com/docs/4.x/api/composables/use-fetch) — return type shape verified against official docs
- Multiple community sources confirm IntersectionObserver sentinel pattern as standard approach for infinite scroll in Vue 3

### Tertiary (LOW confidence)
- Political group color conventions: based on general knowledge of French political parties. Must be verified against actual `political_group` column values in the database after data ingestion.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed except @vueuse/core; versions from package.json
- Architecture: HIGH — patterns verified against official Nuxt 4 and VueUse docs
- Pitfalls: HIGH — SSR hydration, null deputy, race conditions are documented common issues
- Group color mapping: LOW — depends on actual data values not yet verified

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (Nuxt 4 and Tailwind v4 are stable; VueUse API is stable)
