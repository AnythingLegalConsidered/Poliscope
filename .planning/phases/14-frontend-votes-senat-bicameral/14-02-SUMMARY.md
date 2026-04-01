---
phase: 14-frontend-votes-senat-bicameral
plan: 02
subsystem: ui
tags: [nuxt, vue, typescript, bicameral, search, navigation]

requires:
  - phase: 14-01
    provides: ScrutinResultBar component used in SearchResultCard scrutin variant
  - phase: 13-02
    provides: /api/search with type=scrutin support and cross-type FTS

provides:
  - Nav with 4 links (Debats / Votes / Parlementaires / Recherche)
  - Deputies list with chamber filter pills (Tous/AN/Senat)
  - Deputy profile with chamber badge (AN/Senat) in header
  - SearchResultCard with scrutin variant (Vote badge, result bar, /votes/:id link)
  - Search page type filter (Tous/Interventions/Votes) with URL sync

affects:
  - phase-15 (any future phase building on navigation or search)

tech-stack:
  added: []
  patterns:
    - "Chamber filter pills pattern: selectChamber(val) resets page+list, watch includes chamber"
    - "Discriminated component variant: v-if on type prop for conditional rendering"
    - "typeFilter synced to URL query param alongside other search filters"

key-files:
  created:
    - packages/web/app/.planning/phases/14-frontend-votes-senat-bicameral/14-02-SUMMARY.md
  modified:
    - packages/web/app/layouts/default.vue
    - packages/web/app/pages/deputies/index.vue
    - packages/web/app/pages/deputies/[id].vue
    - packages/web/app/components/SearchResultCard.vue
    - packages/web/app/pages/search.vue

key-decisions:
  - "v-if/v-else on type prop for SearchResultCard variants (not separate components) — simpler, one import"
  - "typeFilter pills shown only when results exist or filter already active — avoids confusing empty state"
  - "scrutinId = result.id from API (not context_id) — /api/search normalizes id to scrutin.id for scrutin type"

patterns-established:
  - "Chamber pills: selectChamber resets page + allDeputies before changing ref"
  - "URL sync includes typeFilter in router.replace query alongside existing filters"

duration: 20min
completed: 2026-04-01
---

# Phase 14 Plan 02: Navigation bicamerale + search cross-type Summary

**Nav 4 liens (Votes + Parlementaires), filtre chambre sur /deputies, badge chambre sur profil, SearchResultCard scrutin avec badge Vote bronze et lien /votes/:id, filtre type sur /search**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-01T00:00:00Z
- **Completed:** 2026-04-01T00:20:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Nav globale mise a jour : lien Votes inere entre Debats et Parlementaires (renommage de Deputes)
- /deputies passe de liste AN-only a liste bicamerale avec pills Tous/AN/Senat et titre dynamique
- Profil parlementaire (/deputies/[id]) affiche badge chambre AN ou Senat dans le header
- SearchResultCard accepte un discriminant `type` et rend deux layouts distincts selon intervention/scrutin
- /search ajoute un filtre type (Tous/Interventions/Votes) synce a l'URL et transmis a l'API

## Task Commits

1. **Task 1: Nav + deputies list chamber filter + senator badge** - `2a6e8f8` (feat)
2. **Task 2: SearchResultCard scrutin variant + search.vue type filter** - `7f39f35` (feat)

## Files Created/Modified

- `packages/web/app/layouts/default.vue` — Ajout lien /votes, renommage "Parlementaires"
- `packages/web/app/pages/deputies/index.vue` — Filtre chambre pills, titre dynamique, chambre dans useFetch query
- `packages/web/app/pages/deputies/[id].vue` — Badge chambre AN/Senat dans header, "Retour aux parlementaires"
- `packages/web/app/components/SearchResultCard.vue` — Variant scrutin (v-if type==='scrutin'), props union, formattedDate compatible
- `packages/web/app/pages/search.vue` — typeFilter ref, pills UI, URL sync, template v-for avec type conditionnel

## Decisions Made

- `v-if/v-else` sur prop `type` dans SearchResultCard plutot que deux composants separes : un seul import dans search.vue, coherence du pattern
- `scrutinId = result.id` : l'API /api/search normalise `id` directement au scrutin.id pour le type scrutin (pas de context_id distinct)
- Pills type dans /search apparaissent uniquement quand shouldFetch + resultats presents ou filtre deja actif : evite confusion sur l'etat vide initial

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Plan 14-01 avait ete execute et commite dans une session precedente (commits 27b96db, 2a35e56, f2c4287, 3199f1c). Les composants ScrutinCard, ScrutinResultBar, VotePositionBadge et les pages /votes etaient deja disponibles. Execution de 14-02 directement sans re-executer 14-01.

## Self-Check

### Files exist

- `packages/web/app/layouts/default.vue` — FOUND (modified)
- `packages/web/app/pages/deputies/index.vue` — FOUND (modified)
- `packages/web/app/pages/deputies/[id].vue` — FOUND (modified)
- `packages/web/app/components/SearchResultCard.vue` — FOUND (modified)
- `packages/web/app/pages/search.vue` — FOUND (modified)

### Commits exist

- `2a6e8f8` feat(14-02): bicameral nav + deputies chamber filter + senator badge — FOUND
- `7f39f35` feat(14-02): SearchResultCard scrutin variant + search type filter — FOUND

### TypeScript check

`npx tsc --noEmit` from packages/web — PASSED (zero errors)

## Self-Check: PASSED

## Next Phase Readiness

Phase 14 complete (plans 01 + 02 done). L'interface couvre :
- SC1 + SC2 : /votes liste + detail (plan 01)
- SC3 : badge chambre sur profil depute (plan 02)
- SC4 : nav bicamerale + filtre chambre /deputies (plan 02)
- SC5 : recherche cross-type avec badges distinction (plan 02)

Pret pour phase 15 (si definie) ou release.

---
*Phase: 14-frontend-votes-senat-bicameral*
*Completed: 2026-04-01*
