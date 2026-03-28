---
phase: 07-polish-lancement
plan: 01
subsystem: seo-performance
tags: [seo, sitemap, caching, content-pages]
dependency_graph:
  requires: []
  provides: [global-seo-config, sitemap, api-caching, about-page, legal-page]
  affects: [nuxt.config.ts, all-pages, default-layout]
tech_stack:
  added: ["@nuxtjs/sitemap"]
  patterns: [useSeoMeta, routeRules, defineSitemapEventHandler]
key_files:
  created:
    - server/api/__sitemap__/urls.ts
    - app/pages/about.vue
    - app/pages/legal.vue
    - public/robots.txt
  modified:
    - nuxt.config.ts
    - app/layouts/default.vue
    - app/pages/index.vue
    - app/pages/search.vue
    - app/pages/debates/[id].vue
    - app/pages/deputies/index.vue
    - app/pages/deputies/[id].vue
decisions:
  - id: D-0701-01
    decision: "useSeoMeta with reactive getter functions for dynamic pages"
    context: "SSR renders correctly when data loads asynchronously; static values would be empty on first render"
  - id: D-0701-02
    decision: "Footer-only links to /about and /legal (not in header nav)"
    context: "Plan specified footer only — keeps header nav focused on core app pages"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-28"
  tasks_completed: 3
  tasks_total: 3
---

# Phase 07 Plan 01: SEO, Performance Caching & Content Pages Summary

**One-liner:** Global SEO via `@nuxtjs/sitemap` + `useSeoMeta` on all pages + routeRules caching on API routes + about/legal content pages with footer nav.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Global SEO config + sitemap + routeRules + robots.txt | 5960a1e | nuxt.config.ts, server/api/__sitemap__/urls.ts, public/robots.txt |
| 2 | Per-page useSeoMeta on all pages | 4553c38 | 5 page files updated |
| 3 | About and legal pages + nav links | 1ae013f | app/pages/about.vue, app/pages/legal.vue, app/layouts/default.vue |

## What Was Built

### Global SEO Configuration (nuxt.config.ts)
- `htmlAttrs: { lang: 'fr' }` — sets `<html lang="fr">` globally
- `titleTemplate: '%s — Poliscope'` — all page titles get the suffix automatically
- `@nuxtjs/sitemap` module with dynamic source at `/api/__sitemap__/urls`
- `site.url` from `NUXT_SITE_URL` env (default: `https://poliscope.fr`)
- `routeRules` caching: `/api/debates` 5min, `/api/deputies` 1hr, `/api/deputies/**` 10min

### Sitemap Handler
- `server/api/__sitemap__/urls.ts` queries all debate IDs+dates and deputy IDs
- Returns `{ loc, lastmod? }` objects for `/debates/:id` and `/deputies/:id`
- Uses `defineSitemapEventHandler` from `@nuxtjs/sitemap`

### Per-Page SEO
- All 5 existing pages migrated from `useHead` to `useSeoMeta`
- Dynamic pages (debates/[id] and deputies/[id]) use reactive getter functions for SSR correctness
- OG and Twitter card meta on detail pages (debate: `article`, deputy: `profile`)
- Search page title reactive to query string

### Content Pages
- `/about`: Project description, data sources (DILA), open-source, non-partisan statement
- `/legal`: Mentions légales with 5 sections (éditeur, hébergement, données, propriété, contact)
- Footer in default layout with NuxtLink to `/about` and `/legal`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed useHead referencing route before declaration in search.vue**
- **Found during:** Task 2
- **Issue:** Original `useHead` in search.vue called `route.query.q` before `const route = useRoute()` was declared — would cause runtime error
- **Fix:** Removed legacy `useHead` block, moved `useRoute()` before `useSeoMeta`, used `q` ref (already defined) as reactive getter
- **Files modified:** app/pages/search.vue
- **Commit:** 4553c38

## Verification Results

```
useSeoMeta count: 7 (5 pages + about + legal) ✓
useHead count in pages: 0 ✓
public/robots.txt exists with Sitemap reference ✓
server/api/__sitemap__/urls.ts exists ✓
nuxt.config.ts: titleTemplate, lang=fr, @nuxtjs/sitemap, routeRules ✓
pnpm build: success ✓
```

## Self-Check: PASSED

All files verified present. All 3 commits verified in git log.
