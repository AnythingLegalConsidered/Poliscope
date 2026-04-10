# Phase 17 Punch List

Generated: 2026-04-10
Audit viewports: 1280x800, 768x1024, 390x844
Audit method: Static code review of all 9 pages + 9 components (agent-browser WSL wrapper could not reach Windows localhost; curl confirms server returns 200)
Dev server: http://localhost:3000
Git HEAD at audit: f8c33e9

## Legend
- Severity: blocker | major | minor | nit
- Category: layout | overflow | spacing | typo | responsive | DA | content | bug
- Owner: 17-02 (bug fixes + InterventionCard refactor) | 17-03 (debate detail pagination)

---

## Global (layout/default.vue, app.vue, shared components)

- [ ] **[major][responsive][17-02]** Mobile nav hidden by no wrapper class on `<div class="flex items-center gap-6">` — at 390px the search input and all nav links (Débats, Votes, Parlementaires, Recherche) are inaccessible because the search `<form>` has `hidden sm:block` and the `<nav>` has no breakpoint class but sits inside a flex row that squeezes/overflows. No hamburger menu exists. File: `packages/web/app/layouts/default.vue:L9,L17`. Fix: remove `hidden sm:block` from the form, reduce nav `gap-6` to `gap-3` with `text-xs` at small viewports, or add a simple mobile nav below the header bar.

- [ ] **[minor][responsive][17-02]** Header search input is 192px wide (`w-48`) at all sizes above `sm:` breakpoint — at 768px it may crowd the 4 nav links depending on font rendering. File: `packages/web/app/layouts/default.vue:L13`. Fix: switch to `w-40 lg:w-48` or cap at smaller size on md.

- [ ] **[nit][DA][17-02]** `VotePositionBadge.vue` uses `bg-green-500/10 text-green-700` for "Pour" and `bg-red-500/10 text-red-700` for "Contre" — outside marble/bronze/ink/terracotta palette. Used on `/votes/[id]` vote rows and visible across the app. File: `packages/web/app/components/VotePositionBadge.vue:L18-L21`. Fix: `for` → `bg-bronze/10 text-bronze`, `against` → `bg-terracotta/10 text-terracotta`, `abstain` stays `bg-stone-200 text-ink-muted`.

- [ ] **[nit][DA][17-02]** `ScrutinResultBar.vue` uses `bg-green-500` and `bg-red-400` for the Pour/Contre bar segments — DA violation, these raw utility colors are not in the palette. File: `packages/web/app/components/ScrutinResultBar.vue:L20,L24`. Fix: `bg-green-500` → `bg-bronze`, `bg-red-400` → `bg-terracotta`, `bg-stone-400` → `bg-ink-muted/40`.

- [ ] **[nit][DA][17-02]** `ScrutinCard.vue` result badges use `bg-green-500/10 text-green-700` (Adopté) and `bg-red-500/10 text-red-700` (Rejeté) — DA violations matching the VotePositionBadge pattern. File: `packages/web/app/components/ScrutinCard.vue:L68-L78`. Fix: same as VotePositionBadge — `bg-bronze/10 text-bronze` / `bg-terracotta/10 text-terracotta`.

- [ ] **[nit][DA][17-02]** `SearchResultCard.vue` scrutin variant and intervention variant both use `bg-green-500/10 text-green-700` / `bg-red-500/10 text-red-700` for result badges. File: `packages/web/app/components/SearchResultCard.vue:L95-L97`. Fix: same DA correction.

---

## / (home / pages/index.vue) — NOTE: / IS the debates index, there is no separate /debates route

- [ ] **[minor][responsive][17-02]** Chamber filter pill labels ("Assemblée nationale", "Sénat") are full strings inside `rounded-full px-4 py-1.5` pills. At 390px, "Assemblée nationale" is ~18 chars and wraps or overflows the pill. The three pills together exceed 390px total width. File: `packages/web/app/pages/index.vue:L90-L101`. Fix: abbreviate to "AN" / "Sénat" at small viewport with `sm:hidden`/`hidden sm:inline` spans, or truncate.

- [ ] **[minor][spacing][17-02]** `max-w-7xl mx-auto` on home page vs `max-w-2xl mx-auto` on debate detail — intentional (grid vs thread), but at 768px both may feel different in padding. Audit the `px-4` from the layout container (default.vue:L26) which provides 1rem on all sides — verify no double-padding on smaller viewports.

- [ ] **[nit][content][17-02]** "Tous les débats chargés" end-of-list message uses `text-ink-muted/60` (L136) — opacity modifier on an already muted color may be too faint on marble bg. Nit only, but worth evaluating for readability. File: `packages/web/app/pages/index.vue:L134-L136`. Fix: change to `text-ink-muted/80`.

---

## /debates/[id] (pages/debates/[id].vue)

- [ ] **[blocker][bug][17-03]** API returns ALL interventions for a debate in one payload with no pagination — `await useFetch(\`/api/debates/${route.params.id}\`)` with no page/limit params. Debates with 300-800+ interventions render all cards at once. Slow initial load, DOM pressure on mobile. File: `packages/web/server/api/debates/[id].get.ts` + `packages/web/app/pages/debates/[id].vue:L9`. Fix: add `page`/`limit` query params to API, return pagination metadata, add IntersectionObserver infinite scroll in the frontend (clone deputies/[id].vue pattern).

- [ ] **[major][DA][17-02]** `InterventionCard.vue` — `orderInDebate` prop is received (L20) but never displayed in the template. The metadata is available but hidden from users. File: `packages/web/app/components/InterventionCard.vue:L20,L49-L91`. Fix: add `#{{ orderInDebate }}` as `text-xs text-ink-muted ml-auto` in the header line.

- [ ] **[major][DA][17-02]** `InterventionCard.vue` — `tags` prop is received (L4-L7) but never rendered in the card template. Tag pills exist in `SearchResultCard` but are absent from the thread view. File: `packages/web/app/components/InterventionCard.vue:L3-L8,L73-L91`. Fix: display top 3 tag pills as `text-[10px] bg-marble border border-stone-border rounded-full px-2 py-0.5 text-ink-muted` below content.

- [ ] **[major][DA][17-02]** `InterventionCard.vue` — no visual distinction between consecutive interventions from the same speaker. Every card looks identical regardless of speaker identity. No isContinuation grouping (avatar suppressed + vertical line), no bronze left-border accent for presidential/rapporteur roles. File: `packages/web/app/components/InterventionCard.vue:L49-L91` + parent `pages/debates/[id].vue:L68-L73`. Fix: add `isContinuation` prop (parent computes), bronze `border-l-2` for `speakerRole` keywords (Président, Rapporteur, Ministre).

- [ ] **[minor][content][17-03]** Intervention count display uses `data.interventions?.length ?? 0` (L62) — after pagination this becomes stale (shows only first page count). File: `packages/web/app/pages/debates/[id].vue:L62`. Fix: after pagination, use `data.value?.interventions?.pagination?.total ?? 0`.

- [ ] **[nit][spacing][17-02]** `max-w-2xl mx-auto` on debate detail — at 1280px, debate thread content is very narrow (672px) leaving large empty margins on both sides. Compare to deputy profile which is also `max-w-2xl`. Not a bug per se, but consistent with site design. No change needed — mark as reviewed.

---

## /deputies (pages/deputies/index.vue)

- [ ] **[minor][responsive][17-02]** Group filter `<select>` uses `sm:flex-row` layout with the search input — at 390px it stacks vertically (flex-col) which is correct, but the select dropdown width at 100% is fine. Some LIOT label ("LIOT — Libertés, Indépendants, Outre-mer et Territoires") is very long inside the select — may clip. File: `packages/web/app/pages/deputies/index.vue:L125-L133`. Nit: consider shortening LIOT option label to just "LIOT" since it's a search filter.

- [ ] **[minor][responsive][17-02]** Chamber filter pill labels same issue as home page — "Assemblée nationale" pill too wide for 390px. File: `packages/web/app/pages/deputies/index.vue:L108-L114`. Fix: same abbreviation approach.

- [ ] **[nit][content][17-02]** `selectChamber` is called before `allDeputies` is declared in the code order (L42 calls `allDeputies.value = []` before L48 declares `allDeputies`). Works at runtime due to Vue hoisting but is a code smell. File: `packages/web/app/pages/deputies/index.vue:L41-L48`. Fix: move `allDeputies` declaration above `selectChamber` function, or consolidate reset logic.

---

## /deputies/[id] (pages/deputies/[id].vue)

- [ ] **[major][bug][17-02]** Tag filter reset on pagination — `watch(page, () => { activeTag.value = null })` at L40-L42 wipes the active tag every time the user clicks "Charger plus". The user's filter context is lost on every page load. File: `packages/web/app/pages/deputies/[id].vue:L40-L42`. Fix: remove the `watch(page, ...)` block entirely — `filteredInterventions` computed at L44 re-filters from `allInterventions` correctly on each render.

- [ ] **[major][DA][17-02]** voteStats section uses raw Tailwind color utilities outside the marble/bronze/ink/terracotta palette: `bg-green-100 text-green-800` (Pour), `bg-red-100 text-red-800` (Contre), `bg-gray-100 text-gray-600` (Abstention), `bg-stone-100 text-stone-500` (Absent). File: `packages/web/app/pages/deputies/[id].vue:L162-L165`. Fix: `for` → `bg-bronze/10 text-bronze`, `against` → `bg-terracotta/10 text-terracotta`, `abstain` → `bg-marble-dark text-ink-muted`, `absent` → `bg-marble-dark text-ink-muted/60`.

- [ ] **[minor][responsive][17-02]** Deputy header avatar at `w-20 h-20` (80px) with `flex items-center gap-4` — at 390px the avatar + info row may be tight. The `flex-1 min-w-0` on the info column and `truncate` on the h1 handle overflow, but check that `flex-wrap` on the badges row (L112) wraps cleanly at 390px with long group names. File: `packages/web/app/pages/deputies/[id].vue:L112-L129`. Fix: likely fine but note for viewport check.

- [ ] **[nit][spacing][17-02]** "Charger plus" button uses `rounded-xl` while most other buttons in the app use `rounded-full` for pills or `rounded-lg` for inputs. Inconsistent border-radius. File: `packages/web/app/pages/deputies/[id].vue:L212`. Fix: change to `rounded-lg` to match input style.

---

## /votes (pages/votes/index.vue)

- [ ] **[minor][responsive][17-02]** Two rows of filter pills (chamber row + result row) stacked vertically — at 390px, 3 + 3 = 6 pills across 2 rows, where "Assemblée nationale" pill is again too wide. File: `packages/web/app/pages/votes/index.vue:L88-L111`. Fix: same abbreviation fix, and verify the two filter rows don't visually collide.

- [ ] **[nit][spacing][17-02]** `mb-4` on chamber pills + `mb-6` on result pills — the gap between the two filter rows is `mb-4` (16px). At desktop, slightly tight. Nit only. File: `packages/web/app/pages/votes/index.vue:L88,L101`.

- _No other issues found at 1280/768 from static review._

---

## /votes/[id] (pages/votes/[id].vue)

- [ ] **[major][DA][17-02]** Result badges on scrutin header use `bg-green-500/10 text-green-700` (Adopté) and `bg-red-500/10 text-red-700` (Rejeté) — same DA violation as in ScrutinCard. File: `packages/web/app/pages/votes/[id].vue:L153-L164`. Fix: `bg-bronze/10 text-bronze` / `bg-terracotta/10 text-terracotta`.

- [ ] **[minor][responsive][17-02]** Position filter has 5 pills (Tous, Pour, Contre, Abstention, Absent) inside `flex gap-2 mb-4 flex-wrap`. At 390px these wrap to 2 rows (3+2). The `flex-wrap` handles it gracefully but check alignment. File: `packages/web/app/pages/votes/[id].vue:L194-L225`. Minor only.

- [ ] **[minor][overflow][17-02]** Vote rows use `flex items-center gap-3 py-2` with `flex-1 min-w-0 flex items-center gap-2 flex-wrap` for name+group. At 390px, actor name + GroupBadge + VotePositionBadge in one row may overflow. `flex-wrap` is present but `VotePositionBadge` is `flex-shrink-0` and may push the name. File: `packages/web/app/pages/votes/[id].vue:L252-L265`. Fix: ensure actor name uses `truncate` or `min-w-0`.

- [ ] **[nit][content][17-02]** "Source officielle →" link uses `&rarr;` which renders as "→" — inconsistent with "← Retour" which uses `&larr;`. Minor cosmetic: both are fine, but consider using `→` Unicode directly or keeping `&rarr;` consistently. File: `packages/web/app/pages/votes/[id].vue:L177-L183`.

---

## /search (pages/search.vue)

- [ ] **[minor][UX][17-02]** Type filter pills only appear when `allResults.length > 0 || typeFilter` (L163). On initial page load with results, the pills flash in after render. Users who type fast may not see them appear. Minor UX roughness — not a DA issue. File: `packages/web/app/pages/search.vue:L163`. Fix: consider showing pills as soon as `shouldFetch` is true (even before results arrive), or accept as-is (low impact).

- [ ] **[nit][spacing][17-02]** Tag filter active pill clear button uses `text-bronze` border treatment but the "×" character `<span class="font-bold">×</span>` renders as the × entity, which may be slightly misaligned vertically vs the tag name text. File: `packages/web/app/pages/search.vue:L133-L137`. Fix: use `&times;` or switch to an SVG `×` icon, or ensure consistent line-height.

- _No layout or responsive issues found at 1280/768/390 from static review._

---

## /about (pages/about.vue)

- [ ] **[minor][content][17-02]** About page copy only mentions "Assemblée nationale" — the app now covers the Sénat too (Phases 10-11). Three paragraphs reference only AN data: "l'activité des députés de l'Assemblée nationale", "archives de l'Assemblée nationale", "DILA". File: `packages/web/app/pages/about.vue:L16-L22,L24-L29`. Fix: rewrite to mention both chambers (AN + Sénat), update DILA mention to include Sénat open data, change "des députés" to "des parlementaires".

- [ ] **[minor][content][17-02]** SEO meta description on about.vue still says "agrège les données publiques de l'Assemblée nationale" (L3-L5) — needs same Sénat update. File: `packages/web/app/pages/about.vue:L4`. Fix: update description to mention both chambers.

- _No layout or spacing issues at any viewport — static `max-w-2xl` prose layout is clean._

---

## /legal (pages/legal.vue)

- [ ] **[minor][content][17-02]** Hébergement section shows "À définir." placeholder — hosting is defined: LXC container on Proxmox homelab, nginx reverse proxy, PM2 process manager. File: `packages/web/app/pages/legal.vue:L26`. Fix: fill in real hosting info: "Hébergement personnel — LXC sur Proxmox (homelab), nginx + PM2."

- [ ] **[minor][content][17-02]** Propriété intellectuelle section mentions only "l'Assemblée nationale et la DILA" as data sources — Sénat data is also included. File: `packages/web/app/pages/legal.vue:L42-L47`. Fix: add "et le Sénat" to the data source list.

- _No layout, spacing or responsive issues — static `max-w-2xl` prose layout is clean._

---

## Summary

- 17-02 items: 26
- 17-03 items: 2
- Blockers: 1 | Majors: 9 | Minors: 13 | Nits: 9

### Pre-seeded known issues (all confirmed present)
| # | Issue | Location | Present |
|---|-------|----------|---------|
| 1 | voteStats DA violation (bg-green-100/bg-red-100) | deputies/[id].vue:L162-L165 | ✓ |
| 2 | Mobile nav hidden (search `hidden sm:block`, no mobile nav) | layouts/default.vue:L9,L17 | ✓ |
| 3 | Tag filter reset on pagination (`activeTag.value = null` in watch(page)) | deputies/[id].vue:L40-L42 | ✓ |
| 4 | about.vue mentions only Assemblée nationale | about.vue:L16-L29 | ✓ |
| 5 | legal.vue "Hébergement: À définir." | legal.vue:L26 | ✓ |
| 6 | Debate detail full-payload load (no pagination on /api/debates/[id]) | debates/[id].vue:L9 + server/api/debates/[id].get.ts | ✓ |
