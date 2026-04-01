---
phase: 14-frontend-votes-senat-bicameral
plan: "01"
subsystem: frontend-votes
tags: [vue, nuxt, votes, scrutins, frontend, components]
dependency_graph:
  requires: [13-01]
  provides: [votes-list-page, votes-detail-page, scrutin-components]
  affects: [packages/web/app/pages/votes, packages/web/app/components]
tech_stack:
  added: []
  patterns: [useFetch-with-lazy, infinite-scroll-intersection-observer, filter-reset-anti-pitfall]
key_files:
  created:
    - packages/web/app/components/ScrutinCard.vue
    - packages/web/app/components/ScrutinResultBar.vue
    - packages/web/app/components/VotePositionBadge.vue
    - packages/web/app/pages/votes/index.vue
    - packages/web/app/pages/votes/[id].vue
  modified: []
decisions:
  - "page.value=1 + allScrutins.value=[] in selectChamber/selectResult before changing the ref — prevents duplicates on filter change (same anti-pitfall pattern as deputies/index.vue)"
  - "watch(position, ...) resets allVotes + page before data watcher fires — ensures no stale votes when position filter changes on /votes/[id]"
  - "hasVoteCounts guard before rendering ScrutinResultBar — handles null vote counts from DB (some older scrutins may lack vote breakdown)"
  - "definePageMeta validate on /votes/[id] with /^\\d+$/ — returns 404 for non-numeric slugs, prevents 500"
metrics:
  duration_minutes: 18
  completed: "2026-04-01"
  tasks_completed: 3
  tasks_total: 3
---

# Phase 14 Plan 01: Votes Frontend — List + Detail Pages Summary

**One-liner:** Scrutins list page with dual chamber/result filters + detail page with paginated actor votes, position filter, and visual for/against/abstain bar.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | ScrutinCard, ScrutinResultBar, VotePositionBadge | 27b96db | 3 components created |
| 2 | Page /votes (liste) avec filtres chambre + résultat | 2a35e56 | votes/index.vue |
| 3 | Page /votes/[id] (détail scrutin + votes paginés) | f2c4287 | votes/[id].vue |

## What Was Built

### Components

**ScrutinCard.vue** — clickable NuxtLink card (marble/bronze design system). Displays title, formatted date (fr-FR, Europe/Paris timezone for SSR safety), chamber badge (bronze for AN, ink for Sénat), result badge (green for adopted, red for rejected), scrutin type badge, and embeds ScrutinResultBar when vote counts are non-null.

**ScrutinResultBar.vue** — pure CSS flexbox bar with three colored segments: green (pour), red (contre), stone (abstention). Computes percentages via computed properties. Displays vote counts below the bar as text labels.

**VotePositionBadge.vue** — small color-coded pill badge for vote positions. Maps `for/against/abstain/absent` to French labels and Tailwind color classes (green/red/stone/marble-dark).

### Pages

**pages/votes/index.vue** — paginated scrutin list with:
- Two pill groups: chamber (Tous / AN / Sénat) and result (Tous / Adopté / Rejeté)
- useFetch with `{ page, limit: 20, chamber, result }` query, lazy: true
- IntersectionObserver infinite scroll on sentinel element (rootMargin 200px)
- Filter change resets `page=1` and clears `allScrutins` before changing the ref (prevents duplicate data)
- Dynamic page title computed from active chamber filter

**pages/votes/[id].vue** — scrutin detail page with:
- `definePageMeta validate` rejecting non-numeric IDs → 404, not 500
- Scrutin header: title (font-heading), formatted date, chamber + result badges, ScrutinResultBar, source link
- Position filter pills (Tous / Pour / Contre / Abstention / Absent)
- Paginated actor vote list: photo with initials fallback, NuxtLink to /deputies/:id, GroupBadge, VotePositionBadge
- Infinite scroll on vote list (50 per page)
- Position filter change resets `allVotes=[]` and `page=1` to prevent duplicates

## Verification Results

1. `tsc --noEmit` — PASSED (0 errors)
2. 3 component files present: ScrutinCard.vue, ScrutinResultBar.vue, VotePositionBadge.vue
3. 2 page files present: votes/index.vue, votes/[id].vue
4. Design system adherence: marble/bronze/ink colors, Cinzel font-heading, no shadows

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files verified:
- FOUND: packages/web/app/components/ScrutinCard.vue
- FOUND: packages/web/app/components/ScrutinResultBar.vue
- FOUND: packages/web/app/components/VotePositionBadge.vue
- FOUND: packages/web/app/pages/votes/index.vue
- FOUND: packages/web/app/pages/votes/[id].vue

Commits verified:
- FOUND: 27b96db (feat: ScrutinCard, ScrutinResultBar, VotePositionBadge)
- FOUND: 2a35e56 (feat: /votes list page)
- FOUND: f2c4287 (feat: /votes/[id] detail page)
