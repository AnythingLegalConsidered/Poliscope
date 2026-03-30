---
phase: 11-ingestion-debats-cri
verified: 2026-03-30T17:25:49Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 2/4
  gaps_closed:
    - "Filtre chambre absent dans l API et l UI (Truth 1)"
    - "Donnees Senat non ingérees — pipeline non execute (Truth 2 + 3)"
  gaps_remaining: []
  regressions: []
---

# Phase 11: Ingestion Debats CRI — Rapport de Vérification (Re-vérification)

**Phase Goal:** Toutes les seances publiques de la XVIIe legislature sont en base pour l'AN et le Senat, avec tagging thematique applique aux nouvelles interventions.
**Verified:** 2026-03-30T17:25:49Z
**Status:** passed
**Re-verification:** Oui — apres fermeture des gaps plans 11-03 (filtre chambre UI) et 11-04 (execution pipeline Senat)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Liste debats affiche AN et Senat (filtre chambre fonctionnel) | VERIFIED | API index.get.ts (45 lignes) : param `chamber` lu ligne 8, WHERE `eq(debates.chamber, chamber)` ligne 12-14. index.vue : `chamber = ref<string|undefined>()`, 3 boutons filtre (Tous/AN/Senat), `selectChamber()` reinitialise page+allDebates. DebateCard.vue : badge `AN` (bronze) et `Senat` (ink) conditionnels lignes 37-48. |
| 2 | Debat Senat navigable dans le meme format | VERIFIED | 413 debats Senat en base (SUMMARY plan 11-04). Playwright chamber-filter.spec.ts test "Senat debate thread is navigable" : filtre Senat → click card → URL /debates/NNN → intervention-card visible. |
| 3 | Tags thematiques cross-chamber | VERIFIED | search.get.ts : requete SQL sans filtre chambre (lignes 78-87). 218,535 interventions Senat taguees (81.8% actor match). Playwright test "search returns results from both chambers" : /search?q=budget retourne resultats (chambre-agnostique par design). |
| 4 | Pipeline CRI idempotent (no duplicates) | VERIFIED | ingest_debates_senat.py `insert_interventions()` : DELETE FROM intervention_tags + DELETE FROM interventions WHERE debate_id avant chaque INSERT (lignes 314-319). upsert_debate() via ON CONFLICT DO UPDATE. Pattern identique a ingest_debates.py. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/web/server/api/debates/index.get.ts` | API avec filtre chambre | VERIFIED | 45 lignes. Param `chamber` ligne 8. WHERE clause `eq(debates.chamber, chamber)` lignes 11-14. Expose `chamber` dans SELECT. |
| `packages/web/app/pages/index.vue` | Page liste avec filtre chambre | VERIFIED | 142 lignes. `chamber = ref<string|undefined>()`. 3 boutons filter. `selectChamber()` reset pagination. `useFetch('/api/debates', { query: { page, limit: 20, chamber } })`. Titre dynamique computed. |
| `packages/web/app/components/DebateCard.vue` | Badge chambre AN / Senat | VERIFIED | 62 lignes. `v-if="chamber === 'AN'"` badge bronze + `v-else-if="chamber === 'Senat'"` badge ink. `data-testid="debate-card"` present. |
| `packages/web/e2e/chamber-filter.spec.ts` | Tests E2E filtre chambre | VERIFIED | 114 lignes. 8 tests substantiels : titre, tabs visibles, filtre Senat+badge, filtre AN, navigation thread, search cross-chamber, API ?chamber=Senat, API ?chamber=AN. |
| `packages/ingestion/scripts/ingest_debates_senat.py` | Pipeline Senat CRI | VERIFIED | Existait deja. Bug fixes plan 11-04 : regex filename, lxml recover=True, namespace cri:intervenant, mat-based matching. 413 debats, 292,286 interventions. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| index.vue | /api/debates | ?chamber= reactif (ref) | WIRED | `useFetch` query inclut `chamber` ref, `watch: [page, chamber]` — re-fetch automatique au changement. |
| API index.get.ts | debates table | eq(debates.chamber, chamber) WHERE | WIRED | Drizzle `.where(conditions.length > 0 ? and(...conditions) : undefined)` — filtre actif si chamber fourni. |
| DebateCard.vue | Prop chamber | v-if badge | WIRED | index.vue passe `:chamber="debate.chamber"`. Card affiche badge conditionnel. |
| search.get.ts | interventions (all chambers) | SQL sans WHERE chamber | WIRED | Requete couvre AN + Senat nativement — 218,535 interventions Senat taguees incluses. |
| ingest_debates_senat.py | debates + interventions | upsert + delete-then-insert | WIRED | Idempotence confirmee lignes 294-319. |

### Requirements Coverage

| Requirement | Status | Note |
|-------------|--------|------|
| ~200-300 seances AN en base | SATISFIED | Existait avant phase 11 |
| ~200 seances Senat en base | SATISFIED | 413 seances inserees (surpasse la cible) |
| Filtre chambre fonctionnel | SATISFIED | UI + API implementes et testes E2E |
| Debat Senat meme format AN | SATISFIED | API [id].get.ts chamber-agnostique, InterventionCard reutilise |
| Tags cross-chamber | SATISFIED | 218,535 Senat taguees, search sans filtre chambre |
| Pipeline idempotent | SATISFIED | delete-then-insert dans les deux pipelines |

### Anti-Patterns Found

Aucun bloquant. Les deux anti-patterns de la verification initiale sont resolus :
- Titre hardcode "Debats de l Assemblee nationale" — remplace par `pageTitle` computed (dynamique selon filtre)
- Absence de filtre chambre dans l API — implementee avec WHERE clause Drizzle

### Human Verification Required

Les tests Playwright E2E (9/9 selon plan 11-04 SUMMARY) couvrent les points qui necessitaient une verification humaine dans le rapport initial. Le plan 11-04 documente une approbation "Task 2: Human Verification — APPROVED" apres validation des tests Playwright. Aucun item supplementaire n est identifie.

### Re-verification Summary

Les deux gaps bloquants de la verification initiale sont fermes :

**Gap 1 — Filtre chambre (clos par plan 11-03) :**
- API /api/debates supporte maintenant `?chamber=AN|Senat` avec WHERE Drizzle
- index.vue dispose de 3 boutons filtre reactifs avec reset de pagination
- DebateCard.vue affiche des badges differencies par chambre
- Tests E2E couvrent tous les cas (filtre AN, filtre Senat, API direct, badge visible)

**Gap 2 — Donnees Senat (clos par plan 11-04) :**
- Pipeline ingest_debates_senat.py execute avec succes : 413 debats, 292,286 interventions, 81.8% match
- 218,535 interventions Senat taguees par tag_interventions.py
- 5 bugs corriges durant l execution (regex, lxml, namespace XML, mat-matching, UnboundLocalError)
- Donnees confirmees en base via requetes SQL documentees dans SUMMARY 11-04

Aucune regression detectee sur les items precedemment verifies (idempotence, ingest_debates.py, run_all.py).

---

_Verified: 2026-03-30T17:25:49Z_
_Verifier: Claude (gsd-verifier)_
