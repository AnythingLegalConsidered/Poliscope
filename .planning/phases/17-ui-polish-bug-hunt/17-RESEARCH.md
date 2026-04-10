# Phase 17: UI Polish & Bug Hunt — Research

**Researched:** 2026-04-10
**Domain:** Nuxt 4 frontend polish, Playwright E2E, Vue 3 component refactor, pagination UX
**Confidence:** HIGH (codebase read directly, all key files inspected)

---

## Summary

Phase 17 addresses accumulated visual debt and UX roughness after v2.0's data-focused build-out. The codebase is clean and consistent — the marble/bronze/ink DA is already well applied across all pages. The uncommitted changes in `InterventionCard.vue` and `main.css` (CRI table rendering + HTML sanitization) are Phase 16 carryover work that should be committed before Phase 17 begins.

The biggest concrete pain point is the **debate detail page**: `/api/debates/[id]` returns ALL interventions in a single payload with no pagination support. A debate with 500+ interventions renders every card at once — no virtual scroll, no chunked delivery, no offset/limit. This is the single highest-impact improvement. The second priority is **InterventionCard differentiation**: the current card is minimal and correct but doesn't leverage the DA's visual levers — consecutive speakers repeat avatar/name redundantly, there's no density control, no visual grouping.

The existing Playwright suite (5 spec files, ~22 tests) covers home, deputies, debates, search, and chamber filters well. What's missing entirely: votes pages, vote detail, about, legal, deputy detail, and any responsive/mobile viewport testing. The suite runs headless Chromium only via `@nuxt/test-utils/playwright` with full Nuxt server spun up — solid foundation to extend.

**Primary recommendation:** Execute in 4 plans: (1) commit carryover + visual audit punch list, (2) InterventionCard refactor, (3) debate detail pagination, (4) Playwright suite extension. Plans 2 and 3 are independent and can be authored in parallel; Plan 4 depends on Plans 2+3 being merged so tests validate the final state.

---

## Page Inventory & Bug Audit

### Pages and what they render

| Route | File | Renders | Key data dependencies |
|-------|------|---------|----------------------|
| `/` | `pages/index.vue` | Debate cards grid, chamber filter pills, infinite scroll | `/api/debates` paginated |
| `/debates/[id]` | `pages/debates/[id].vue` | ALL interventions, debate header | `/api/debates/[id]` — **no pagination** |
| `/deputies` | `pages/deputies/index.vue` | Deputy cards grid, chamber filter, group filter, search, infinite scroll | `/api/deputies` paginated |
| `/deputies/[id]` | `pages/deputies/[id].vue` | Deputy header, tag stats, voteStats, interventions paginated (load-more) | `/api/deputies/[id]` |
| `/votes` | `pages/votes/index.vue` | Scrutin cards grid, chamber+result filter pills, infinite scroll | `/api/votes` paginated |
| `/votes/[id]` | `pages/votes/[id].vue` | Scrutin header, result bar, individual votes paginated (infinite scroll) | `/api/votes/[id]` |
| `/search` | `pages/search.vue` | Search input, results (intervention + scrutin cards), tag/type filters, infinite scroll | `/api/search` |
| `/about` | `pages/about.vue` | Static prose, no data | — |
| `/legal` | `pages/legal.vue` | Static prose, no data | — |

### Likely bug categories per page

**Layout/max-width inconsistency:**
- Home/Deputies/Votes use `max-w-7xl` (wide grid)
- Debates/[id], Deputies/[id], Search, About, Legal use `max-w-2xl` or `max-w-3xl`
- This is intentional (thread vs. grid) but the transitions at breakpoints should be audited for jarring feel on tablet

**Mobile responsiveness gaps (HIGH likelihood):**
- Header nav: 4 links + search hidden on mobile (`hidden sm:block`). On mobile, no nav is visible except the logo. No hamburger menu. This is a functional gap on small viewports.
- Chamber filter pills on home/votes/deputies: 3 pills fit on desktop but may wrap awkwardly on narrow mobile
- Deputy card grid `lg:grid-cols-3` collapses to 1 col on mobile — fine, but check gap/padding
- Debate card grid same issue
- Vote detail `max-w-3xl` — check vote row items don't overflow on 320px viewport

**Specific known visual issues (from code reading):**
- `voteStats` on deputy profile uses raw Tailwind color classes (`bg-green-100 text-green-800`, `bg-red-100`, etc.) that are NOT from the marble/bronze DA. These green/red utility classes break the DA. They need bronze/marble equivalents or semantic DA colors.
- `about.vue` content says "Assemblée nationale" only — the app now covers Sénat too. Text is stale.
- `legal.vue` has "Hébergement: À définir." — placeholder still in production

**Empty states:**
- All pages have empty states — these are consistent and correct
- No skeleton loaders — only `LoadingSpinner`. Not a bug but a polish opportunity.

**Typography:**
- Headings use `font-heading` (Cinzel) correctly throughout
- `font-body` (Inter) applied via body — consistent
- No rogue font-family overrides spotted in component files

**InterventionCard specific:**
- `orderInDebate` is received as a prop but **never displayed** in the card. This metadata is available but hidden.
- Tags prop is received but **never displayed** in the InterventionCard template (only in SearchResultCard which has tag pills). Tags exist in the data but go unused in the thread view.
- No visual distinction between interventions — every card looks identical regardless of speaker, length, or position

**Search page:**
- Type filter pills only appear when results exist OR `typeFilter` is active — this means on initial load with results, the pills flash in after render. Minor UX roughness.

### Audit approach recommendation

**Single-pass per page, not grouped by bug type.** Reason: most bugs are co-located — a page's layout, responsive, and typography bugs all surface together when you open it at 3 viewports. Grouping by bug type requires revisiting each page multiple times.

Audit matrix:
1. Desktop (1280px) — layout, typography, spacing, data correctness
2. Tablet (768px) — breakpoint transitions, filter pill wrapping
3. Mobile (390px) — nav usability, card density, overflow

---

## Intervention Card Differentiation

### Current state

`packages/web/app/components/InterventionCard.vue` (as read, which IS the committed+uncommitted state):
- Avatar left (40x40 rounded-full, bronze bg initials fallback) — already Twitter-pattern
- Name + GroupBadge + role in header line
- Content below (plain text or HTML for tables)
- Simple `border-b border-stone-border/50` separator
- No order number, no tags display, no consecutive grouping, no timestamp/context link

The template is clean and correct but has no visual hierarchy levers.

### "Twitter old-school" concretely, mapped to parliamentary context

Twitter old-school (pre-2023) characteristics that translate:

| Twitter pattern | Parliamentary equivalent | Feasible within DA? |
|----------------|--------------------------|---------------------|
| Avatar anchors the left column consistently | Keep 40px avatar column | Already done |
| Compact header: name + @handle + timestamp inline | Name + GroupBadge + order number inline | YES — add `#N` in ink-muted |
| Dense text, no excessive padding | Reduce `py-4` to `py-3`, tighten gap | YES |
| Consecutive tweets from same user collapse avatar (reply threading visual) | Consecutive interventions from same speaker: hide avatar, show indent line | YES — add `isFirstInRun` computed |
| Thin left border accent for "your tweet" vs others | Bronze left border on president/rapporteur interventions | YES — `speakerRole` has this data |
| Reply/quote context shown above | No inter-intervention reference data in current API — skip | Out of scope |
| Timestamp is secondary metadata | `orderInDebate` as secondary `#N` | YES |

### Visual levers available within the DA

All these stay within marble/bronze/ink — no new colors needed:

1. **Bronze left-border accent rule** (`border-l-2 border-bronze`) for speakers with `speakerRole` (President, Rapporteur, Ministre) — differentiates official speech from floor debate
2. **Consecutive speaker grouping** — when `intervention[n].deputyId === intervention[n-1].deputyId`, suppress the avatar, replace with a subtle `2px` vertical ink-muted/20 line in the avatar column to show thread continuity
3. **Ink weight on name** — already `font-semibold` — can upgrade first-in-run to slightly larger (`text-sm` → `text-[0.9375rem]`) for visual anchor
4. **Order number as secondary metadata** — `#{{ orderInDebate }}` in `text-xs text-ink-muted` at the end of the header line, or as a tiny left-gutter annotation
5. **Tag pills** — the data is already available (tags prop exists, `interventionTags` is fetched) — display top 2-3 tags as tiny pills `text-[10px] bg-marble border border-stone-border rounded-full` below content
6. **Content truncation** — long interventions (>500 chars) could be collapsed with `line-clamp-4` + "Lire la suite" expand, reducing page scroll weight; this is a polish item for debate detail but applies to InterventionCard universally

### Consecutive speaker grouping — implementation pattern

The grouping logic must live in the **parent** (debate `[id].vue`) not in the card itself, because the card doesn't know its predecessor. Pattern:

```vue
<!-- In debates/[id].vue -->
<InterventionCard
  v-for="(intervention, idx) in data.interventions"
  :key="intervention.id"
  v-bind="intervention"
  :is-continuation="idx > 0 && data.interventions[idx - 1].deputyId === intervention.deputyId"
/>
```

The card receives `isContinuation: boolean` prop. When true: hide avatar, show thin vertical line in its place, omit name/group header line.

### Reply/citation — data availability

The `interventions` table has `order_in_debate` but **no foreign key to a cited intervention**. The XML source (CRI) contains some `<intervention>` nesting but that's not preserved in the current schema. Implementing inter-intervention references would require schema work — **out of scope for Phase 17**.

---

## Debate Detail Pagination

### Current API behavior

`/api/debates/[id]` (`packages/web/server/api/debates/[id].get.ts`):
- Fetches ALL interventions for a debate in one query
- No `page`/`limit`/`offset` parameters
- Returns `{ debate, interventions: [...all] }`
- The page component receives `data.interventions` (an array) and renders all with `v-for`

### Scale estimate

DB not directly queryable from this session. From project context: "thousands of interventions" per the phase description. Parliamentary session CRI documents are typically 30-400 interventions for normal sessions, with budget sessions (PLF) reaching 600-1200+. Worst-case estimate: ~800-1000 interventions for a full-day budget séance.

At 800 interventions × ~2KB DOM nodes each = ~1600 elements rendered at once. This causes:
- Long initial render (~500ms-2s depending on client)
- Scroll performance degradation (layout thrashing on scroll)
- Potential memory pressure on mobile

### Pagination strategies evaluated

| Strategy | SEO | UX | Implementation cost | Recommendation |
|----------|-----|----|--------------------|----------------|
| Numbered pages (`?page=2`) | HIGH (crawlable) | LOW (breaks reading flow) | MEDIUM | No |
| Load-more button | MEDIUM (page 1 indexed) | GOOD | LOW | **YES — primary** |
| Infinite scroll (IntersectionObserver) | LOW (only p1 crawled) | BEST | LOW (pattern already in codebase) | Acceptable secondary |
| Virtual scroll (windowed) | N/A | BEST | HIGH (requires library: `vue-virtual-scroller` or `@tanstack/vue-virtual`) | No — overkill |
| Jump-to-speaker index | N/A | USEFUL | MEDIUM | Nice-to-have addon |
| Section/chapter breaks | N/A | GOOD | MEDIUM-HIGH (requires XML parsing carryover) | No — data not available |

### Recommended approach: server-side pagination + IntersectionObserver infinite scroll

This is the same pattern already used on the deputies profile page (`/deputies/[id]`), which does paginated `load-more` on interventions. Reuse that exact pattern for debates.

**API changes needed:**
1. Add `page`, `limit` query params to `/api/debates/[id]`
2. Return `{ debate, interventions: { data: [...], pagination: { page, limit, total, totalPages } } }`
3. Default `limit=50` (50 interventions is a readable chunk — ~5-10 minutes of debate)

**Frontend changes needed:**
1. Add `page = ref(1)` and `allInterventions = ref([])` accumulator
2. Add sentinel div + `useIntersectionObserver` (already imported via `@vueuse/core`)
3. The `data.interventions.length` count in the header becomes `data.interventions?.pagination?.total ?? 0`

**SEO consideration:** Debate detail pages are indexed. The first 50 interventions are rendered on initial load (SSR/hydration) — fully crawlable. Deep pages are loaded client-side only, which is acceptable; Google doesn't need intervention #347 to understand the debate.

**Existing pattern to clone:** `packages/web/app/pages/deputies/[id].vue` lines 9-52 (fetch with `watch: [page]`, accumulator watch, hasMore computed, load-more button).

### What about the `inArray` tag fetch?

Currently the API does `inArray(interventionTags.interventionId, interventionIds)` for all intervention IDs at once. With pagination, this becomes `inArray(...page_ids)` — correct and actually faster since each page is at most 50 IDs.

---

## Playwright Test Suite

### Current state

**Location:** `packages/web/e2e/`
**Config:** `packages/web/playwright.config.ts` — Chromium only, 60s timeout, `@nuxt/test-utils` integration (spins up real Nuxt server)
**Run command:** `cd packages/web && playwright test`

| File | Tests | Coverage |
|------|-------|---------|
| `home.spec.ts` | 3 | Home page load, infinite scroll, debate card navigation |
| `deputies.spec.ts` | 3 | Deputies list, search filter, card navigation |
| `debate.spec.ts` | 2 | Debate detail render, intervention card speaker names |
| `search.spec.ts` | 3 | Header search nav, results render, empty state |
| `chamber-filter.spec.ts` | 9 | Chamber filter tabs, AN/Senat badge verification, API direct tests |
| **Total** | **20** | — |

### What's missing (phase goal: "couvrir chaque page")

| Page/Feature | Currently covered | Missing |
|---|---|---|
| Home | YES | Responsive mobile viewport |
| Debates list | Via home nav only | Direct `/debates` URL (no such page — debates are at `/`) |
| Debate detail | YES (basic) | Pagination controls after Phase 17 change; intervention count display; console errors |
| Deputies list | YES | Mobile viewport; group filter |
| Deputy detail `/deputies/[id]` | NO | Page load, h1, voteStats render, tag filter, intervention list |
| Votes list `/votes` | NO | Page load, h1, filter pills, scrutin cards |
| Vote detail `/votes/[id]` | NO | Page load, result bar, votes list, position filter |
| Search | YES | Type filter (intervention/scrutin) |
| About | NO | Page load, h1 |
| Legal | NO | Page load, h1 |
| Nav links | NO | All nav links clickable, correct destinations |
| Footer links | NO | About + legal links |
| Mobile viewport | NO | All pages at 390px |
| Console errors | NO | `page.on('pageerror')` global listener |

### Test categories to add

**Smoke tests** (page loads, no 500, h1 visible):
```typescript
// Pattern for each missing page
test('votes page loads', async ({ page, goto }) => {
  await goto('/votes', { waitUntil: 'hydration' })
  await expect(page.locator('h1')).toBeVisible()
  // check no console errors via page.on('pageerror')
})
```

**Lisibility tests** (semantic structure):
- `h1` present and non-empty
- `main` landmark exists (via `<main>` in layout)
- No broken images (check `img[alt]` — all images have alt)
- No obvious overflow (no horizontal scrollbar at 1280px)

**Coherence tests** (DA consistency, cross-page navigation):
- Header nav links all resolve to 200
- Footer links (about, legal) resolve
- Bronze color applied to active nav link (`active-class="text-bronze"`)
- `data-testid` attributes present on all card types

**Console error detection** — add globally to every test:
```typescript
// In playwright.config.ts or a beforeEach hook
page.on('pageerror', (err) => {
  throw new Error(`Browser console error: ${err.message}`)
})
```

**Responsive testing:**
- Add a `mobile` project to `playwright.config.ts`:
```typescript
{ name: 'mobile-chrome', use: { ...devices['iPhone 14'] } }
```
- Smoke tests run on both projects
- Mobile-specific: check nav is usable (even if just logo visible), no horizontal scroll

### axe-core accessibility — recommendation

`@axe-core/playwright` is available in the ecosystem and integrates directly with the existing setup. Given Phase 17 scope and time budget, recommend **not** adding it in this phase — axe failures would balloon scope. Flag it for Phase 18 instead.

### Running tests

Current command: `cd packages/web && pnpm test:e2e` (maps to `playwright test`)

No changes to test command needed. After adding mobile project to config, `playwright test --project=chromium` runs desktop only; `playwright test` runs all projects.

---

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `@playwright/test` | ^1.58.2 | E2E test runner | Already installed |
| `@nuxt/test-utils` | ^4.0.0 | Nuxt server integration for Playwright | Already installed |
| `@vueuse/core` | ^14.2.1 | `useIntersectionObserver` for infinite scroll | Already used |
| `isomorphic-dompurify` | ^3.8.0 | XSS-safe HTML render for CRI tables | Already installed |

### No new dependencies needed

Pagination, InterventionCard refactor, and test extension all use existing stack. Do not add:
- Virtual scroll library (overkill for this scale)
- axe-core (out of scope)
- Visual regression tool (overkill — Playwright screenshots without a baseline service add noise)

---

## Architecture Patterns

### Pattern 1: Paginated infinite scroll (debate detail)

Clone the pattern from `packages/web/app/pages/deputies/[id].vue` lines 9-52:
- `page = ref(1)`, `allItems = ref([])`, fetch with `watch: [page]`
- `watch(data, ...)` accumulates pages
- `hasMore` computed from pagination
- IntersectionObserver sentinel OR load-more button

**Debate detail vs deputy profile difference:** Debate detail currently uses `await useFetch` (blocking SSR). Keep SSR for the first batch (page 1). Add `lazy: true, watch: [page]` pattern only for subsequent pages — or simply add `?page=1&limit=50` to the initial fetch and use the same approach as deputies.

### Pattern 2: InterventionCard isContinuation prop

Parent computes whether each card continues the previous speaker:
```vue
:is-continuation="idx > 0 && data.interventions[idx-1].deputyId !== null && data.interventions[idx-1].deputyId === intervention.deputyId"
```

Card receives `isContinuation: boolean` (optional, defaults false). When true:
- Avatar column: show `w-10 h-10` div with vertical `border-l-2 border-stone-border` centered, no image
- Header line: suppress name/GroupBadge row entirely
- Reduce top padding: `py-3` instead of `py-4`

Only group when both have a `deputyId` (known actor). Unknown speakers (`deputyId = null`) are never grouped.

### Pattern 3: Bronze left-border for role-based interventions

```vue
<div
  :class="[
    'flex gap-3 py-4 border-b border-stone-border/50',
    isPresidentialRole ? 'border-l-2 border-bronze pl-3' : ''
  ]"
>
```

`isPresidentialRole` computed: check `speakerRole` for keywords (Président, Présidente, Rapporteur, Rapporteuse, M. le ministre, Mme la ministre). This list is finite and known from the CRI data.

### Pattern 4: Order number display

Add `#{{ orderInDebate }}` in the header line, right-aligned or appended after role:
```vue
<span class="text-xs text-ink-muted ml-auto">#{{ orderInDebate }}</span>
```

### Anti-Patterns to Avoid

- **Adding shadows:** The DA explicitly has no shadows. No `shadow-*` Tailwind utilities.
- **Adding new colors outside the palette:** The voteStats green/red issue is a known DA violation — fix it (use `text-ink`, `text-bronze`, `text-ink-muted` equivalents) rather than extend it.
- **Virtual scrolling for this dataset:** At 800 items, the DOM cost is real but manageable with server-side pagination. Virtual scroll adds complexity, breaks CMD+F, breaks anchor links.
- **Infinite scroll for SEO-sensitive pages:** The debate detail is already SSR-rendered for page 1. Loading via infinite scroll for pages 2+ is acceptable — these are not distinct crawlable URLs.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Intersection observer for scroll | Custom event listener | `useIntersectionObserver` from `@vueuse/core` (already used) |
| HTML sanitization | Custom regex stripping | `isomorphic-dompurify` (already installed) |
| Playwright test server setup | Custom express + vite | `@nuxt/test-utils/playwright` (already configured) |
| Responsive breakpoints | Custom media queries in CSS | Tailwind's `sm:`, `md:`, `lg:` prefixes |

---

## Common Pitfalls

### Pitfall 1: Debate detail SSR + pagination

**What goes wrong:** Adding `lazy: true` to the initial fetch breaks SSR — the page hydrates empty, then loads data client-side. This degrades SEO and causes layout shift.

**How to avoid:** Keep `await useFetch` for page 1 (SSR-safe). For subsequent pages, either: (a) use a second `useFetch` with `lazy: true` triggered by page watcher, or (b) change the initial fetch to `useFetch('/api/debates/[id]', { query: { page: 1, limit: 50 } })` — SSR gives page 1 normally. Client-side pagination adds pages 2+.

**Warning sign:** White flash on debate detail load, or Nuxt hydration mismatch errors in console.

### Pitfall 2: InterventionCard isContinuation with null deputyId

**What goes wrong:** Non-parliamentary speakers (minister, government member) have `deputyId = null`. Two consecutive null-deputyId interventions by different people would incorrectly merge their visual grouping if grouping on `null === null`.

**How to avoid:** Only group when `deputyId !== null`. Null speakers are always shown standalone.

### Pitfall 3: voteStats DA violation regression

**What goes wrong:** The `bg-green-100 text-green-800` etc. classes on voteStats are already merged. Fixing them in Phase 17 could cause visual regression if tests screenshot-compare against current state.

**How to avoid:** No screenshot baseline exists — safe to fix. The DA fix: use `bg-marble-dark text-ink` for neutral states, and for Pour/Contre consider `text-bronze`/`text-terracotta` from the DA palette rather than green/red.

### Pitfall 4: Playwright flakiness on IntersectionObserver

**What goes wrong:** Infinite scroll tests (`page.evaluate(() => window.scrollTo(0, scrollHeight))`) are inherently flaky — IntersectionObserver may not fire synchronously after scroll in headless mode.

**How to avoid:** Keep the existing pattern (scroll + `waitForTimeout(2000)`) but add `waitForLoadState('networkidle')` after timeout. For the test suite extension, prefer testing pagination via API (`page.request.get(...)`) or the load-more button pattern rather than synthetic scroll.

### Pitfall 5: Mobile nav — no hamburger menu

**What goes wrong:** On mobile, the header shows only the logo (nav is `hidden sm:block`, search is `hidden sm:block`). There's no mobile navigation at all.

**How to avoid:** The audit must flag this as a bug. Phase 17 should add a minimal mobile nav (hamburger or bottom bar). This is a functional gap, not merely cosmetic. However, given scope, a simple approach: make nav links visible at all sizes (remove `hidden sm:block` from nav, adjust for smaller font-size or abbreviate labels).

### Pitfall 6: Tag filter reset on page change (deputies profile)

**What goes wrong:** In `deputies/[id].vue`, `watch(page, () => { activeTag.value = null })` resets the tag filter whenever the user loads more interventions. This means paginating forward loses the user's filter context.

**How to avoid:** This is an existing bug — flag it in the audit. Fix: the tag filter should persist across pages. The `allInterventions` accumulator already holds all pages; the `filteredInterventions` computed re-filters correctly. The issue is just the `watch(page, () => activeTag.value = null)` which should be removed.

---

## Uncommitted Changes — Handle First

Two files are modified but not committed (from `git status`):

| File | Change | Action |
|------|--------|--------|
| `packages/web/app/components/InterventionCard.vue` | CRI table HTML rendering with DOMPurify | Commit as carryover before Phase 17 starts |
| `packages/web/app/assets/css/main.css` | `.intervention-html` table styles | Commit together with above |
| `packages/web/package.json` | Unknown (listed in git status) | Inspect and commit or revert |
| `pnpm-lock.yaml` | Lock file update | Commit with package.json change |

These are clean, working changes (DOMPurify for XSS-safe table rendering). They belong in a "chore: commit Phase 16 carryover" commit before Phase 17 work begins.

---

## Wave/Sequencing Recommendation

### Plan structure (4 plans)

```
Plan 17-01: Carryover commit + Visual audit punch list
  - Commit the 4 uncommitted files
  - Systematic audit of all 9 pages at 3 viewports
  - Produce a concrete punch list (labeled bugs with file:line)
  - No fixes yet — just the list

Plan 17-02: InterventionCard refactor [INDEPENDENT]
  - isContinuation prop + consecutive grouping
  - Bronze left-border for presidential/role interventions
  - orderInDebate display (#N)
  - Tags display (top 3 pills)
  - voteStats DA fix (green/red → bronze/terracotta/ink-muted)
  - mobile nav fix (remove hidden sm:block from nav)
  - All other audit punch list bug fixes

Plan 17-03: Debate detail pagination [INDEPENDENT from 17-02]
  - Add page/limit to /api/debates/[id]
  - Frontend: accumulator + IntersectionObserver sentinel
  - Update intervention count display (pagination.total)

Plan 17-04: Playwright suite extension [DEPENDS ON 17-02 + 17-03]
  - Add mobile viewport project to playwright.config.ts
  - Smoke tests for all uncovered pages (votes, vote detail, deputy detail, about, legal)
  - Console error detection via page.on('pageerror')
  - Nav coherence tests
  - Responsive tests (390px viewport)
```

**Why 17-01 first:** The audit produces the definitive bug list. 17-02 implements it. Without the audit, 17-02 risks missing bugs or fixing non-issues.

**Why 17-02 and 17-03 in parallel:** Zero shared files. InterventionCard is `components/InterventionCard.vue`. Pagination touches `pages/debates/[id].vue` and `server/api/debates/[id].get.ts`. No conflict.

**Why 17-04 last:** Tests should validate the final UI. Writing tests against a broken or unfinished InterventionCard means either writing tests that pass broken state, or having to update tests twice.

---

## Open Questions

1. **Intervention count at worst case**
   - What we know: "thousands of interventions" per phase description, PLF debates are longest
   - What's unclear: actual max (couldn't query DB from this session — psql not available on host)
   - Recommendation: Before implementing pagination, run `SELECT debate_id, COUNT(*) FROM interventions GROUP BY debate_id ORDER BY 2 DESC LIMIT 5` on the prod DB to choose an appropriate default limit (25, 50, or 100)

2. **mobile nav approach**
   - What we know: current nav is `hidden sm:block`, no mobile nav exists
   - What's unclear: user preference for hamburger vs. bottom bar vs. condensed inline
   - Recommendation: Simplest fix — remove `hidden sm:block` from nav in `default.vue`, keep links, reduce font to `text-xs`, let them wrap or abbreviate. Avoids adding JS toggle state.

3. **Stale about.vue content**
   - "Assemblée nationale" only, doesn't mention Sénat
   - Simple text fix — but needs editorial decision on new text

---

## Sources

### Primary (HIGH confidence)
- Direct read of all 9 page files, 9 component files, 5 Playwright spec files, playwright.config.ts, nuxt.config.ts, main.css, package.json
- Git diff showing uncommitted changes in InterventionCard.vue and main.css

### Secondary (MEDIUM confidence)
- Phase description from ROADMAP.md
- Pattern inference from existing `deputies/[id].vue` pagination (confirmed working from git history)

### Tertiary (LOW confidence)
- Worst-case intervention count: estimated from domain knowledge of French parliamentary CRI documents, not measured from live DB

---

## Metadata

**Confidence breakdown:**
- Page inventory: HIGH — all files read directly
- Bug categories: HIGH for code-visible issues, MEDIUM for responsive (not visually tested)
- InterventionCard refactor: HIGH — patterns are clear, DA constraints known
- Pagination strategy: HIGH — API code read, existing pattern proven
- Playwright gaps: HIGH — all spec files read, gaps identified precisely
- Worst-case intervention count: LOW — DB not queryable from this session

**Research date:** 2026-04-10
**Valid until:** Stable — no external dependencies introduced

## RESEARCH COMPLETE
