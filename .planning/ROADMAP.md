# Poliscope — Roadmap

## Milestone 1 : MVP — Debats de l'AN

### Phase 1 — Setup & Infrastructure
**Objectif** : Projet Nuxt 4 fonctionnel avec PostgreSQL, pret a developper.
- Init Nuxt 4 + TypeScript + Tailwind CSS v4
- Docker Compose (app + PostgreSQL)
- ORM setup (Drizzle) + schema DB initial (5 tables)
- Structure du projet (dossiers, conventions Nuxt 4)
- **Livrable** : `docker compose up` lance l'app sur localhost
- **Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Scaffold Nuxt 4 + Tailwind CSS v4 + structure projet
- [x] 01-02-PLAN.md — Docker Compose + Drizzle schema + health check API

### Phase 2 — Ingestion des donnees AN
**Objectif** : Pipeline Python qui peuple la DB avec les debats reels de l'AN.
- Explorer l'API open data de l'AN (endpoints, formats)
- Script de recuperation des deputes (identite, photo, groupe)
- Script de recuperation des seances et interventions
- Parsing et normalisation des donnees
- Tagging automatique par mots-cles
- Ingestion incrementale
- **Livrable** : DB peuplee avec les debats de la legislature en cours
- **Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — Python env + modules partages + ingestion deputes
- [x] 02-02-PLAN.md — Ingestion seances + interventions
- [x] 02-03-PLAN.md — Tagging thematique + orchestrateur pipeline

### Phase 3 — API Backend
**Objectif** : API routes Nuxt qui exposent les donnees pour le frontend.
- GET /api/debates — liste des seances (paginee)
- GET /api/debates/:id — interventions d'une seance
- GET /api/deputies — liste des deputes
- GET /api/deputies/:id — profil + interventions
- GET /api/search — recherche full-text avec filtres
- **Livrable** : API testable qui retourne les donnees correctement
- **Plans:** 3 plans

Plans:
- [x] 03-01-PLAN.md — Pagination utility + debates endpoints
- [x] 03-02-PLAN.md — Deputies endpoints with filters and profile
- [x] 03-03-PLAN.md — Full-text search endpoint

### Phase 4 — UI Debats (Thread View)
**Objectif** : Page principale — les debats affiches comme des threads Twitter.
- Page d'accueil avec liste des debats recents
- Page debat avec thread scrollable
- Composant intervention (avatar, nom, groupe, texte)
- Scroll infini / pagination
- Design responsive mobile-first
- **Livrable** : On peut scroller un debat de l'AN comme un thread Twitter
- **Plans:** 3 plans

Plans:
- [x] 04-01-PLAN.md — Shared components (GroupBadge, InterventionCard, LoadingSpinner) + group colors
- [x] 04-02-PLAN.md — Home page with debates list + infinite scroll
- [x] 04-03-PLAN.md — Debate thread page (Twitter-style intervention thread)

### Phase 5 — Profils Deputes
**Objectif** : Pages profils avec historique des interventions.
- Page profil depute (info + stats)
- Liste des interventions filtrables
- Navigation profil <-> debat
- **Livrable** : On peut voir tout ce qu'un depute a dit
- **Plans:** 2 plans

Plans:
- [x] 05-01-PLAN.md — Deputies list page with search, group filter, infinite scroll
- [x] 05-02-PLAN.md — Deputy profile page with stats, tag filter, bidirectional navigation

### Phase 6 — Recherche & Filtres
**Objectif** : Moteur de recherche puissant pour retrouver n'importe quelle citation.
- Barre de recherche globale
- Full-text search PostgreSQL avec highlighting
- Filtres (depute, date, tag)
- Page resultats avec extraits contextuels
- **Livrable** : On peut chercher "immigration" et trouver toutes les interventions sur le sujet
- **Plans:** 2 plans

Plans:
- [x] 06-01-PLAN.md — Search results page + SearchResultCard + FTS highlight styling
- [x] 06-02-PLAN.md — Global header search bar + full search UX verification

### Phase 7 — Polish & Lancement
**Objectif** : Finitions avant mise en ligne.
- SEO (meta tags, sitemap, structured data)
- Performance (lazy loading, caching)
- Page "A propos" + mentions legales
- Tests E2E sur les parcours principaux
- **Livrable** : App prete pour un hebergement public
- **Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md — SEO + performance caching + sitemap + content pages (about, legal)
- [x] 07-02-PLAN.md — Playwright E2E tests for critical user journeys

---

## Milestone 2 : Base de Donnees Parlementaire Universelle

**Objectif** : BDD PostgreSQL complete de toutes les donnees parlementaires francaises (XVIIe legislature), hebergee sur LXC dedie PVE02, exposee via API REST universelle et frontend adapte.
**Architecture** : Monorepo pnpm (packages/shared + packages/ingestion + packages/web)
**Infra** : LXC Debian 12 — 4 vCPU, 4 Go RAM, 100 Go disk
**Scope donnees** : CRI (AN + Senat), Scrutins/Votes, Acteurs bicameraux, Organes
**V3 (deferred)** : Questions, Amendements, Dossiers legislatifs, CR Commissions

---

### Phase 8 — Monorepo & Infra LXC

**Goal** : Le repo est restructure en monorepo pnpm fonctionnel et le LXC PVE02 est operationnel avec PostgreSQL 17 accessible depuis le dev local.
**Depends on** : Phase 7 (Milestone 1 complete)
**Requirements** : INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE) :
  1. `pnpm dev` depuis la racine du monorepo lance le frontend Nuxt sans erreur de module resolution
  2. `nuxt build` (pas seulement `nuxt dev`) reussit — les workspace packages sont resolus correctement par Vite
  3. Un operateur peut se connecter a PostgreSQL 17 sur le LXC depuis sa machine de dev (psql -h [LXC_IP])
  4. Les scripts Python existants s'executent depuis packages/ingestion sans changer leurs imports

**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md — Restructuration monorepo pnpm (packages/shared, packages/ingestion, packages/web)
- [x] 08-02-PLAN.md — Provisionnement LXC Debian 12 sur PVE02 + PostgreSQL 17 + acces reseau

---

### Phase 9 — Schema BDD Universel

**Goal** : Le schema PostgreSQL couvre tous les types de donnees parlementaires cibles (acteurs, organes, seances, scrutins, votes) et les 2 479 interventions existantes sont migrees sans perte.
**Depends on** : Phase 8 (monorepo + LXC operationnels)
**Requirements** : SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04, SCHEMA-05, SCHEMA-06, SCHEMA-07, SCHEMA-08
**Success Criteria** (what must be TRUE) :
  1. La table `actors` contient les 618 deputes migres depuis `deputies` — aucune perte de donnees (count identique, FTS fonctionnel)
  2. Les 2 479 interventions existantes sont accessibles via les endpoints Nuxt apres migration — zero regression visible en frontend
  3. La table `cross_references` existe et peut mapper un ID PA vers un slug nosdeputes et un ID DILA numerique
  4. `drizzle-kit generate` produit des migrations incrementales (pas de DROP TABLE sur les donnees existantes)
  5. Les index FTS francais (`search_vector tsvector`) existent sur acteurs et interventions — `EXPLAIN ANALYZE` confirme un index scan

**Plans:** 3 plans

Plans:
- [x] 09-01-PLAN.md — Rename deputies -> actors (hand-written migration) + stored tsvector FTS + delete schema duplicate + update API routes
- [x] 09-02-PLAN.md — Add tables (organs, legislatures, scrutins, votes, questions, amendments, cross_references) + debates.chamber + additive migration
- [x] 09-03-PLAN.md — Gap closure: fix index name inconsistency + apply migrations to live DB + verify data integrity

---

### Phase 10 — Ingestion Acteurs & Organes

**Goal** : La base contient tous les acteurs parlementaires de la XVIIe legislature (deputes AN + senateurs) et leurs organes d'appartenance, avec une table cross-reference qui mappe les IDs entre toutes les sources.
**Depends on** : Phase 9 (schema deploye)
**Requirements** : INGEST-01, INGEST-02, INGEST-03, INGEST-09
**Success Criteria** (what must be TRUE) :
  1. La table `actors` contient ~577 deputes AN et ~348 senateurs XVIIe, chacun avec chambre, groupe politique, et photo
  2. La table `cross_references` mappe chaque acteur vers son ID source (PA prefix pour AN, LA/PO pour Senat) — zero acteur orphelin dans `ingestion_warnings`
  3. Les pipelines acteurs et organes sont idempotents — re-lancer deux fois produit le meme resultat (pas de doublons, upsert correct)
  4. Les organes (commissions permanentes, groupes politiques) sont en base avec leurs membres et periodes de mandat

**Plans:** 2 plans

Plans:
- [ ] 10-01-PLAN.md — Migration 0003 (cross_references unique) + AN deputies ZIP pipeline + Senat senators API pipeline + cross-references
- [ ] 10-02-PLAN.md — AN + Senat organs ingestion + political_group resolution + run_all.py orchestrator update

---

### Phase 11 — Ingestion Debats CRI (AN + Senat)

**Goal** : Toutes les seances publiques de la XVIIe legislature sont en base pour l'AN et le Senat, avec tagging thematique applique aux nouvelles interventions.
**Depends on** : Phase 10 (acteurs et cross-references en base — FK root)
**Requirements** : INGEST-04, INGEST-05, INGEST-08
**Success Criteria** (what must be TRUE) :
  1. La liste des debats affiche des seances AN et Senat (filtre chambre fonctionnel) — ~200-300 seances AN, ~200 seances Senat
  2. Un utilisateur peut ouvrir un debat du Senat et lire le thread d'interventions dans le meme format que les debats AN
  3. Les nouvelles interventions (AN + Senat) ont des tags thematiques assigns — la recherche par tag retourne des resultats des deux chambres
  4. Le pipeline CRI supporte le re-run sans doublons (idempotent) — les seances deja en base sont mises a jour, pas dupliquees

**Plans** : TBD

Plans:
- [ ] 11-01-PLAN.md — Refactoring pipeline CRI AN vers nouveau schema acteurs + ingestion complete XVIIe
- [ ] 11-02-PLAN.md — Pipeline CRI Senat (Akoma Ntoso XML) + tagging etendu sur nouvelles interventions

---

### Phase 12 — Ingestion Votes & Scrutins

**Goal** : Les scrutins publics de l'AN et du Senat sont en base avec la position de vote de chaque parlementaire, accessibles via API.
**Depends on** : Phase 10 (acteurs), Phase 11 (sessions pour FK scrutin->seance)
**Requirements** : INGEST-06, INGEST-07
**Success Criteria** (what must be TRUE) :
  1. L'API /api/votes retourne la liste des scrutins avec filtre par chambre (AN/Senat) — ~500 scrutins AN attendus
  2. L'API /api/votes/:id retourne le detail d'un scrutin avec la position (pour/contre/abstention/absent) de chaque parlementaire
  3. Un utilisateur peut voir sur le profil d'un parlementaire son historique de votes — les scrutins sont lies a l'acteur via actor_id
  4. Les pipelines scrutins AN et Senat sont idempotents et tournent independamment

**Plans** : TBD

Plans:
- [ ] 12-01-PLAN.md — Pipeline scrutins/votes AN (data.assemblee-nationale.fr Scrutins.json.zip)
- [ ] 12-02-PLAN.md — Pipeline scrutins/votes Senat (Dosleg dump via staging container)

---

### Phase 13 — API REST Universelle + OpenAPI

**Goal** : Tous les endpoints API sont stables, documentes, et couvrent les nouvelles donnees (votes, filtre chambre, recherche cross-type) avec une doc Swagger accessible.
**Depends on** : Phase 12 (toutes les donnees en base)
**Requirements** : API-01, API-02, API-03, API-04, API-05, API-06
**Success Criteria** (what must be TRUE) :
  1. Les endpoints debates et deputies existants continuent de fonctionner avec les nouvelles donnees — zero regression
  2. GET /api/votes et GET /api/votes/:id retournent des donnees correctement formatees avec filtre chambre operationnel
  3. Tous les endpoints existants acceptent un parametre `chambre` (AN/Senat) — les resultats sont filtrables par chambre
  4. La recherche full-text retourne des resultats de type "debat" et "vote" dans la meme reponse (cross-type)
  5. Swagger UI est accessible a /api/docs — chaque endpoint y est documente avec schemas de requete et reponse

**Plans** : TBD

Plans:
- [ ] 13-01-PLAN.md — Extension endpoints existants (chambre filter, deputies->actors alias) + endpoints /api/votes
- [ ] 13-02-PLAN.md — FTS cross-type (stored search_vector + materialized view) + OpenAPI via @scalar/nuxt

---

### Phase 14 — Frontend Votes, Senat & Bicameral

**Goal** : L'interface permet d'explorer les votes et les debats du Senat avec la meme UX que l'AN, et la navigation bicamerale est claire.
**Depends on** : Phase 13 (API stable)
**Requirements** : UI-01, UI-02, UI-03, UI-04, UI-05, UI-06
**Success Criteria** (what must be TRUE) :
  1. Un utilisateur peut consulter la liste des scrutins avec filtre par chambre et voir qui a vote quoi sur un scrutin donne
  2. Les debats du Senat apparaissent dans la liste des debats — un filtre chambre (AN/Senat/Tous) est disponible
  3. Un profil senateur est accessible avec le meme niveau d'information qu'un profil depute (interventions, votes, groupe)
  4. La navigation entre AN et Senat est evidente — un toggle ou filtre global de chambre est present sur les pages liste
  5. La recherche retourne des resultats de type "vote" avec un badge distinctif — un utilisateur peut filtrer par type de resultat

**Plans** : TBD

Plans:
- [ ] 14-01-PLAN.md — Pages scrutins (liste + detail) + profils senateurs
- [ ] 14-02-PLAN.md — Navigation bicamerale (filtre chambre global) + recherche cross-type avec type badges

---

### Phase 15 — Deploiement & Ops

**Goal** : L'application tourne en production sur le LXC PVE02 avec backup automatique et refresh hebdomadaire des donnees.
**Depends on** : Phase 14 (frontend stable), Phase 8 (LXC provisionne)
**Requirements** : OPS-01, OPS-02, OPS-03, OPS-04
**Success Criteria** (what must be TRUE) :
  1. Poliscope est accessible publiquement depuis le LXC PVE02 — l'URL de production charge l'app
  2. `pg_dump` tourne via systemd timer et produit un backup .sql.gz — le dernier backup a moins de 24h
  3. Le refresh des donnees parlementaires se declenche automatiquement via systemd timer hebdomadaire — les nouvelles seances apparaissent sans intervention manuelle
  4. Un endpoint /api/health retourne un status JSON avec l'etat de la DB et la date du dernier refresh

**Plans** : TBD

Plans:
- [ ] 15-01-PLAN.md — Deploy app sur LXC (provision.sh, PostgreSQL config, Nuxt PM2/systemd)
- [ ] 15-02-PLAN.md — Backup pg_dump + systemd timers (refresh hebdo) + health check endpoint

---

## Progress

**Milestone 1 (Phases 1-7) :** Complete — 2026-03-28
**Milestone 2 (Phases 8-15) :** In progress

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
| 9. Schema BDD Universel | v2.0 | 2/3 | Gap closure | - |
| 10. Ingestion Acteurs & Organes | v2.0 | 0/2 | Not started | - |
| 11. Ingestion Debats CRI | v2.0 | 0/2 | Not started | - |
| 12. Ingestion Votes & Scrutins | v2.0 | 0/2 | Not started | - |
| 13. API REST Universelle | v2.0 | 0/2 | Not started | - |
| 14. Frontend Votes, Senat & Bicameral | v2.0 | 0/2 | Not started | - |
| 15. Deploiement & Ops | v2.0 | 0/2 | Not started | - |
