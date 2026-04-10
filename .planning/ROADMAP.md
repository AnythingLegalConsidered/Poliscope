# Poliscope — Roadmap

## Milestones

- ✅ **v1.0 MVP — Debats de l'AN** — Phases 1-7 (shipped 2026-03-28)
- ✅ **v2.0 Base de Donnees Parlementaire Universelle** — Phases 8-16 (shipped 2026-04-05)
- 🚧 **v2.1 UI Polish & Bug Hunt** — Phase 17 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP — Debats de l'AN (Phases 1-7) — SHIPPED 2026-03-28</summary>

- [x] Phase 1: Setup & Infrastructure (2/2 plans) — completed 2026-03-27
- [x] Phase 2: Ingestion AN (3/3 plans) — completed 2026-03-27
- [x] Phase 3: API Backend (3/3 plans) — completed 2026-03-27
- [x] Phase 4: UI Debats (3/3 plans) — completed 2026-03-28
- [x] Phase 5: Profils Deputes (2/2 plans) — completed 2026-03-28
- [x] Phase 6: Recherche & Filtres (2/2 plans) — completed 2026-03-28
- [x] Phase 7: Polish & Lancement (2/2 plans) — completed 2026-03-28

</details>

<details>
<summary>✅ v2.0 Base de Donnees Parlementaire Universelle (Phases 8-16) — SHIPPED 2026-04-05</summary>

- [x] Phase 8: Monorepo & Infra LXC (2/2 plans) — completed 2026-03-28
- [x] Phase 9: Schema BDD Universel (3/3 plans) — completed 2026-03-28
- [x] Phase 10: Ingestion Acteurs & Organes (3/3 plans) — completed 2026-03-30
- [x] Phase 11: Ingestion Debats CRI (4/4 plans) — completed 2026-03-30
- [x] Phase 12: Ingestion Votes & Scrutins (2/2 plans) — completed 2026-03-31
- [x] Phase 13: API REST Universelle (2/2 plans) — completed 2026-04-01
- [x] Phase 14: Frontend Votes, Senat & Bicameral (2/2 plans) — completed 2026-04-01
- [x] Phase 15: Deploiement & Ops (2/2 plans) — completed 2026-04-03
- [x] Phase 16: Cleanup & Polish v2.0 (1/1 plan) — completed 2026-04-05

</details>

## Progress

**Milestone 1 (Phases 1-7) :** Complete — 2026-03-28
**Milestone 2 (Phases 8-16) :** Complete — 2026-04-05

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Setup & Infrastructure | v1.0 | 2/2 | Complete | 2026-03-27 |
| 2. Ingestion AN | v1.0 | 3/3 | Complete | 2026-03-27 |
| 3. API Backend | v1.0 | 3/3 | Complete | 2026-03-27 |
| 4. UI Debats | v1.0 | 3/3 | Complete | 2026-03-28 |
| 5. Profils Deputes | v1.0 | 2/2 | Complete | 2026-03-28 |
| 6. Recherche & Filtres | v1.0 | 2/2 | Complete | 2026-03-28 |
| 7. Polish & Lancement | v1.0 | 2/2 | Complete | 2026-03-28 |
| 8. Monorepo & Infra LXC | v2.0 | 2/2 | Complete | 2026-03-28 |
| 9. Schema BDD Universel | v2.0 | 3/3 | Complete | 2026-03-28 |
| 10. Ingestion Acteurs & Organes | v2.0 | 3/3 | Complete | 2026-03-30 |
| 11. Ingestion Debats CRI | v2.0 | 4/4 | Complete | 2026-03-30 |
| 12. Ingestion Votes & Scrutins | v2.0 | 2/2 | Complete | 2026-03-31 |
| 13. API REST Universelle | v2.0 | 2/2 | Complete | 2026-04-01 |
| 14. Frontend Votes, Senat & Bicameral | v2.0 | 2/2 | Complete | 2026-04-01 |
| 15. Deploiement & Ops | v2.0 | 2/2 | Complete | 2026-04-03 |
| 16. Cleanup & Polish v2.0 | v2.0 | 1/1 | Complete | 2026-04-05 |
| 17. UI Polish & Bug Hunt | v2.1 | 0/? | Not planned | — |

### Phase 17: UI Polish & Bug Hunt

**Goal:** Eliminer tous les bugs d'affichage, ameliorer la lisibilite et la differenciation des interventions/commentaires (inspiration Twitter old-school tout en gardant la DA marble/bronze DataCommune), paginer les pages debats trop longues, et couvrir chaque page via tests Playwright CLI.

**Scope:**
- Audit visuel systematique de chaque page (home, debats, debat detail, deputes, depute detail, votes, vote detail, search, about, legal)
- Bug fixes d'affichage (layout, overflow, spacing, typo, responsive)
- Refonte cards interventions : meilleure differenciation visuelle entre prises de parole (inspiration Twitter old-school, DA DataCommune conservee)
- Pagination page debat detail (actuellement monolithique et lourde)
- Suite de tests Playwright CLI : smoke + lisibilite + coherence sur chaque page et fonction principale

**Out of scope (v3):**
- Highlight automatique des moments importants (trop complexe, deferre)
- Refonte complete DA

**Depends on:** Phase 16

**Plans:** TBD (run /gsd:plan-phase 17 to break down)
