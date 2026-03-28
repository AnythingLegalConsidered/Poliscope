# Phase 7: Polish & Lancement — Research

**Researched:** 2026-03-28
**Domain:** Nuxt 4 SEO / Performance / E2E Testing / Deployment
**Confidence:** HIGH (core findings verified against official Nuxt 4 docs and Playwright docs)

---

## Summary

Phase 7 covers four distinct domains that must all ship together before the app goes public: SEO (meta tags, sitemap, structured data), performance (lazy loading, caching), content pages (A propos, mentions légales), and E2E tests. Each domain has a well-established pattern in Nuxt 4 with minimal hand-rolling needed — the ecosystem provides modules for everything.

The existing codebase already has `useHead` on two pages (`debates/[id].vue`, `deputies/[id].vue`), so the SEO pattern is already introduced. The gap is: no global defaults in `nuxt.config.ts`, no `useSeoMeta` for OG/Twitter cards, no sitemap, no structured data, and no E2E tests at all. Performance-wise, Nuxt 4 handles most optimizations automatically — the main gains come from `routeRules` caching on API routes and ensuring images use `<NuxtImg>` (though this app is mostly text/data, so image impact is minimal).

Deployment is Docker SSR via `node .output/server/index.mjs` — already in use from Phase 1. No changes needed to the Docker setup; Phase 7 only needs environment variables confirmed and a final `nuxt build` verification.

**Primary recommendation:** Use `useSeoMeta` for per-page SEO + `@nuxtjs/sitemap` for auto-generated sitemap + Playwright with `@nuxt/test-utils` for E2E. Add `routeRules` for API caching. All via official modules — zero custom solutions.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `useSeoMeta` (built-in) | Nuxt 4 | Type-safe meta tags, OG, Twitter cards | Built into Nuxt 4 via Unhead, zero install, full TypeScript, XSS-safe |
| `useHead` (built-in) | Nuxt 4 | Head title, JSON-LD script injection | Already in use in the project |
| `@nuxtjs/sitemap` | latest | XML sitemap at `/sitemap.xml` | Official Nuxt module, auto-discovers routes |
| `@playwright/test` | latest | E2E browser automation | Industry standard, first-class Nuxt 4 support |
| `@nuxt/test-utils` | latest | Nuxt-aware Playwright integration | Official Nuxt testing package, handles dev server lifecycle |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@nuxtjs/robots` | latest | robots.txt with sitemap link | Optional — can hand-write robots.txt instead for a simple app |
| `nuxt-schema-org` (part of `@nuxtjs/seo`) | latest | JSON-LD structured data via `useSchemaOrg()` | Only worth it if rich snippets are wanted (debate pages = Article, deputy pages = Person) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@nuxtjs/sitemap` | Hand-written `/public/sitemap.xml` | Static sitemap won't include dynamic debate/deputy URLs |
| `@nuxt/test-utils` Playwright integration | Plain `@playwright/test` against running server | Less integrated — must manually start/stop dev server |
| `nuxt-schema-org` | Raw `useHead` with JSON-LD script | More verbose, but zero extra dependency |

**Installation:**
```bash
pnpm add -D @playwright/test @nuxt/test-utils
pnpm add @nuxtjs/sitemap
npx playwright install chromium
```

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── pages/
│   ├── about.vue          # Page "A propos"
│   └── legal.vue          # Mentions légales
├── layouts/
│   └── default.vue        # Already exists — add global useSeoMeta here
e2e/
├── home.spec.ts           # Debates list + infinite scroll smoke test
├── debate.spec.ts         # Debate detail page
├── deputies.spec.ts       # Deputies list + search
├── search.spec.ts         # Global search bar + results page
playwright.config.ts
```

### Pattern 1: Global SEO defaults in nuxt.config.ts

**What:** Set site-wide title template, charset, viewport, lang, and default description once. Per-page overrides via `useSeoMeta` or `useHead`.
**When to use:** Always — prevents missing meta on pages that forget to call `useSeoMeta`.

```typescript
// Source: https://nuxt.com/docs/getting-started/seo-meta
// nuxt.config.ts
export default defineNuxtConfig({
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      titleTemplate: '%s — Poliscope',
      meta: [
        { name: 'description', content: "Explorez les débats et l'activité des députés de l'Assemblée nationale" },
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
      ],
    },
  },
})
```

### Pattern 2: Per-page useSeoMeta

**What:** Full OG + Twitter card meta on pages that have unique content.
**When to use:** All dynamic pages — debates/[id], deputies/[id], search results.

```typescript
// Source: https://nuxt.com/docs/api/composables/use-seo-meta
// In pages/debates/[id].vue — replaces existing useHead
useSeoMeta({
  title: () => (data.value?.debate?.title ?? 'Débat') + ' — Poliscope',
  description: () => data.value?.debate?.title ?? '',
  ogTitle: () => data.value?.debate?.title ?? 'Débat',
  ogDescription: () => data.value?.debate?.title ?? '',
  ogType: 'article',
  twitterCard: 'summary',
})
```

### Pattern 3: Sitemap with dynamic routes

**What:** `@nuxtjs/sitemap` auto-discovers static routes. Dynamic routes (debates, deputies) need a sources endpoint.
**When to use:** Required — `/debates/[id]` and `/deputies/[id]` are not auto-crawlable at build time without a source.

```typescript
// nuxt.config.ts
export default defineNuxtConfig({
  modules: ['@nuxtjs/sitemap'],
  site: {
    url: 'https://poliscope.fr',
    name: 'Poliscope',
  },
  sitemap: {
    sources: ['/api/__sitemap__/urls'],
  },
})
```

```typescript
// server/api/__sitemap__/urls.ts
export default defineSitemapEventHandler(async () => {
  const [debates, deputies] = await Promise.all([
    // Query all debate IDs from DB
    // Query all deputy IDs from DB
  ])
  return [
    ...debates.map(d => ({ loc: `/debates/${d.id}`, lastmod: d.date })),
    ...deputies.map(d => ({ loc: `/deputies/${d.id}` })),
  ]
})
```

### Pattern 4: API route caching with routeRules

**What:** Add stale-while-revalidate caching to heavy API endpoints via `routeRules` in `nuxt.config.ts`.
**When to use:** API routes that query the database on every request and whose data changes infrequently.

```typescript
// Source: https://nuxt.com/docs/guide/best-practices/performance
export default defineNuxtConfig({
  routeRules: {
    '/api/debates': { cache: { maxAge: 60 * 5 } },         // 5 min SWR
    '/api/deputies': { cache: { maxAge: 60 * 60 } },        // 1 hour
    '/api/deputies/**': { cache: { maxAge: 60 * 10 } },     // 10 min per deputy
    '/api/debates/**': { cache: { maxAge: 60 * 5 } },       // 5 min per debate
  },
})
```

Note: Search endpoint (`/api/search`) should NOT be cached — queries vary per user input.

### Pattern 5: Playwright E2E with @nuxt/test-utils

**What:** Playwright tests that start the Nuxt dev server automatically and run browser assertions.
**When to use:** All critical user journeys (5-6 spec files max for this app size).

```typescript
// Source: https://nuxt.com/docs/getting-started/testing
// playwright.config.ts
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'
import type { ConfigOptions } from '@nuxt/test-utils/playwright'

export default defineConfig<ConfigOptions>({
  testDir: './e2e',
  use: {
    nuxt: {
      rootDir: fileURLToPath(new URL('.', import.meta.url)),
    },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
```

```typescript
// e2e/home.spec.ts
import { expect, test } from '@nuxt/test-utils/playwright'

test('home page loads debates list', async ({ page, goto }) => {
  await goto('/', { waitUntil: 'hydration' })
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.locator('[data-testid="debate-card"]').first()).toBeVisible()
})

test('global search bar navigates to search page', async ({ page, goto }) => {
  await goto('/', { waitUntil: 'hydration' })
  await page.fill('input[type="search"]', 'budget')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/search\?q=budget/)
})
```

### Pattern 6: Static content pages (A propos, Mentions légales)

**What:** Simple Vue pages with no API calls — pure content.
**When to use:** A propos describes the project; Mentions légales covers legal obligations under French law for a public website.

```typescript
// app/pages/about.vue
<script setup lang="ts">
useSeoMeta({
  title: 'À propos — Poliscope',
  description: 'Poliscope est un outil indépendant de transparence parlementaire.',
})
</script>
```

Add nav link to `default.vue` layout.

### Anti-Patterns to Avoid

- **Caching `/api/search`:** Search results vary per query — caching produces wrong results for different queries on the same cached key.
- **`nuxt generate` for this app:** The app needs SSR (dynamic data from DB). Use `nuxt build` + Node.js server, not static generation.
- **Missing `data-testid` on cards:** Without stable locators, Playwright tests become brittle. Add `data-testid` to `DebateCard`, `DeputyCard`, and search result cards.
- **Per-page JSON-LD with hand-rolled `useHead` script injection:** The output is hard to validate and easy to get wrong. Either use `nuxt-schema-org` or skip JSON-LD for V1.
- **Running `playwright install` without `--with-deps` in CI:** Will fail on headless Linux environments.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML sitemap for dynamic routes | Manual `/public/sitemap.xml` | `@nuxtjs/sitemap` | Static file misses new debates/deputies; module handles `<lastmod>`, priorities, multi-sitemap |
| robots.txt with sitemap reference | `/public/robots.txt` (manual) | `/public/robots.txt` (static OK for simple case) | App has no crawl restrictions; a static file is fine here |
| OG meta tag management | Raw `<meta>` in `useHead` | `useSeoMeta` | `useSeoMeta` is typed — prevents `name` vs `property` confusion for OG tags |
| E2E server lifecycle | `beforeAll(() => startServer())` | `@nuxt/test-utils/playwright` | Handles build, start, and teardown — avoids port conflicts and stale builds |

**Key insight:** For this app's scale, the "don't hand-roll" principle mainly applies to the sitemap. Everything else (meta tags, robots, simple pages) is minimal enough that the built-in Nuxt APIs suffice.

---

## Common Pitfalls

### Pitfall 1: Dynamic routes missing from sitemap
**What goes wrong:** `/debates/42` and `/deputies/15` never appear in sitemap because the crawler can't find them at build time.
**Why it happens:** Static route discovery only finds routes in the `pages/` directory — dynamic segments aren't crawled.
**How to avoid:** Implement a `server/api/__sitemap__/urls.ts` handler that queries the database and returns all IDs.
**Warning signs:** `sitemap.xml` only shows `/`, `/search`, `/deputies`, `/about`, `/legal` — no ID-based URLs.

### Pitfall 2: useSeoMeta reactivity — SSR vs. client
**What goes wrong:** OG tags are empty/wrong when the page is server-side rendered because `data.value` is null during initial SSR fetch.
**Why it happens:** `useFetch` with `lazy: true` defers the fetch to client — server renders before data arrives.
**How to avoid:** Use getter functions `() => data.value?.title ?? 'Poliscope'` in `useSeoMeta` — they resolve reactively. Or remove `lazy: true` on pages where SEO tags are critical (debate/deputy detail pages).
**Warning signs:** Social preview links show "Poliscope" title instead of the debate/deputy name.

### Pitfall 3: Playwright flakiness on infinite scroll
**What goes wrong:** Tests that assert "first card is visible" fail intermittently because the API call hasn't returned yet.
**Why it happens:** `{ waitUntil: 'hydration' }` doesn't wait for data fetching to complete.
**How to avoid:** Use `page.waitForSelector('[data-testid="debate-card"]')` or assert with `await expect(locator).toBeVisible()` which retries automatically.
**Warning signs:** Tests pass locally but fail in CI.

### Pitfall 4: routeRules cache with query parameters
**What goes wrong:** `/api/debates?page=2` returns the same cached response as `/api/debates?page=1`.
**Why it happens:** Default Nitro cache key may not include query params depending on configuration.
**How to avoid:** Verify cache behavior with `?page=2` manually before shipping. If needed, add `varies: ['query']` to cache config or use `cachedEventHandler` directly in route handlers.
**Warning signs:** Infinite scroll loads the same 20 debates repeatedly.

### Pitfall 5: Missing `lang="fr"` on `<html>`
**What goes wrong:** Screen readers and search engines treat the page as English.
**Why it happens:** Nuxt doesn't set `lang` by default.
**How to avoid:** Set `htmlAttrs: { lang: 'fr' }` in `nuxt.config.ts` `app.head`.
**Warning signs:** Google Search Console language detection shows "en" for French content.

---

## Code Examples

Verified patterns from official sources:

### Global head in nuxt.config.ts
```typescript
// Source: https://nuxt.com/docs/getting-started/seo-meta
export default defineNuxtConfig({
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      titleTemplate: '%s — Poliscope',
      charset: 'utf-8',
      viewport: 'width=device-width, initial-scale=1',
      meta: [
        { name: 'description', content: "Transparence parlementaire — débats et activité des députés" },
      ],
    },
  },
})
```

### useSeoMeta with reactive data
```typescript
// Source: https://nuxt.com/docs/api/composables/use-seo-meta
useSeoMeta({
  title: () => `${data.value?.deputy?.fullName ?? 'Député'} — Poliscope`,
  ogTitle: () => data.value?.deputy?.fullName ?? 'Poliscope',
  description: () => `Activité parlementaire de ${data.value?.deputy?.fullName ?? 'ce député'}`,
  ogType: 'profile',
  twitterCard: 'summary',
})
```

### Sitemap dynamic source handler
```typescript
// Source: https://nuxtseo.com/docs/sitemap/getting-started/installation
// server/api/__sitemap__/urls.ts
import { defineSitemapEventHandler } from '#imports'
import { db } from '~/server/db'
import { debates, deputies } from '~/server/db/schema'

export default defineSitemapEventHandler(async () => {
  const [allDebates, allDeputies] = await Promise.all([
    db.select({ id: debates.id, date: debates.date }).from(debates),
    db.select({ id: deputies.id }).from(deputies),
  ])
  return [
    ...allDebates.map(d => ({
      loc: `/debates/${d.id}`,
      lastmod: d.date ?? undefined,
    })),
    ...allDeputies.map(d => ({ loc: `/deputies/${d.id}` })),
  ]
})
```

### Playwright critical journey test
```typescript
// Source: https://nuxt.com/docs/getting-started/testing
import { expect, test } from '@nuxt/test-utils/playwright'

test('search flow — header to results', async ({ page, goto }) => {
  await goto('/', { waitUntil: 'hydration' })
  const searchInput = page.locator('input[type="search"]')
  await searchInput.fill('budget')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/search\?q=budget/)
  await expect(page.getByText(/résultat/i)).toBeVisible()
})

test('debate detail page renders title', async ({ page, goto }) => {
  await goto('/debates/1', { waitUntil: 'hydration' })
  await expect(page.locator('h1')).not.toBeEmpty()
})
```

### routeRules caching
```typescript
// Source: https://nuxt.com/docs/guide/best-practices/performance
export default defineNuxtConfig({
  routeRules: {
    '/api/debates': { cache: { maxAge: 300 } },
    '/api/debates/**': { cache: { maxAge: 300 } },
    '/api/deputies': { cache: { maxAge: 3600 } },
    '/api/deputies/**': { cache: { maxAge: 600 } },
    // Do NOT cache /api/search — query varies per user
  },
})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `head()` option in `defineComponent` | `useHead()` / `useSeoMeta()` composables | Nuxt 3+ | Composables are reactive, tree-shakeable |
| Manual meta `property` vs `name` distinction | `useSeoMeta` typed object | Nuxt 3.3+ | Eliminates common OG meta mistakes |
| `nuxt-sitemap` (community) | `@nuxtjs/sitemap` (official) | 2023+ | Now part of the official nuxt-seo suite |
| Jest for Nuxt testing | Vitest + `@nuxt/test-utils` | Nuxt 3+ | Vitest is the recommended runner; Playwright for E2E |

**Deprecated/outdated:**
- `vue-meta`: replaced by Unhead (built into Nuxt 3/4)
- `@nuxtjs/sitemap` v2.x: major API change in v4.x — ensure fresh install, not docs from old tutorials

---

## Open Questions

1. **Does the DB have enough debates/deputies for sitemap to be meaningful?**
   - What we know: Phase 2 ingested data from the AN public API
   - What's unclear: Row counts (could be 500 debates or 50,000)
   - Recommendation: Query counts before deciding on sitemap pagination; module handles up to 50,000 URLs per sitemap file automatically

2. **Should debate/deputy detail pages be prerendered or SSR?**
   - What we know: Data changes infrequently (parliamentary sessions); Docker SSR is the current setup
   - What's unclear: How often data is re-ingested
   - Recommendation: Keep SSR with `routeRules` caching for now; can migrate to ISR later if needed

3. **What deployment URL will be used?**
   - What we know: Docker Compose setup from Phase 1 exists
   - What's unclear: Final hostname for `NUXT_SITE_URL` in sitemap config
   - Recommendation: Use env variable `NUXT_SITE_URL` — let the planner create a `.env.example` task

4. **JSON-LD structured data — is it in scope for V1?**
   - What we know: Phase description says "structured data" is an objective
   - What's unclear: Whether `nuxt-schema-org` (extra dependency) or raw `useHead` JSON-LD injection is preferred
   - Recommendation: Use raw `useHead` with a JSON-LD script for simplicity — no extra module needed for basic WebSite + WebPage schema

---

## Sources

### Primary (HIGH confidence)
- https://nuxt.com/docs/getting-started/seo-meta — `useHead`, `useSeoMeta`, `titleTemplate`, global head config
- https://nuxt.com/docs/getting-started/testing — `@nuxt/test-utils` Playwright setup, `playwright.config.ts`, `goto` helper
- https://nuxt.com/docs/guide/best-practices/performance — `routeRules`, lazy components, `NuxtLink` prefetch
- https://nuxt.com/docs/getting-started/deployment — `nuxt build`, `node .output/server/index.mjs`, Node.js preset
- https://playwright.dev/docs/writing-tests — locators, assertions, `beforeEach`, form interactions

### Secondary (MEDIUM confidence)
- https://nuxtseo.com/docs/sitemap/getting-started/installation — `@nuxtjs/sitemap` install and `sources` config (official module docs, verified against nuxt.com/modules/sitemap registry entry)
- https://nuxt.com/modules/sitemap — module registry page confirms `@nuxtjs/sitemap` is official

### Tertiary (LOW confidence)
- https://nuxtseo.com/docs/schema-org/getting-started/introduction — `nuxt-schema-org` API (partially fetched, module docs not fully verified)
- https://masteringnuxt.com/blog/nuxt-4-performance-optimization-complete-guide-to-faster-apps-in-2026 — third-party performance guide (unverified, but consistent with official docs)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `useSeoMeta`, `useHead`, Playwright all verified against official Nuxt 4 docs
- Architecture: HIGH — patterns derived from official docs code examples
- Sitemap dynamic sources: MEDIUM — module docs partially fetched; pattern is consistent across sources
- Pitfalls: MEDIUM — verified pitfall 1-3 against known Nuxt behavior; pitfall 4 (cache key query params) is LOW (single source, but plausible)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable ecosystem — Nuxt 4, Playwright change infrequently)
