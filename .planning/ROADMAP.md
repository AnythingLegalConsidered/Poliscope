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

**Objectif** : BDD PostgreSQL complete de toutes les donnees parlementaires francaises (XVIIe legislature), hebergee sur LXC dedie PVE02, exposee via API REST universelle.
**Architecture** : Monorepo (packages/api + packages/web)
**Infra** : LXC Debian 12 — 4 vCPU, 4 Go RAM, 100 Go disk
**Scope donnees** : Niveau 3 complet (CRI, QAG, Questions, Amendements, Votes, Dossiers, Commissions)

### Phase 8 — Monorepo & Infra LXC
**Objectif** : Restructurer le repo en monorepo et provisionner le LXC PVE02.
- Restructurer en packages/api + packages/web
- Migrer le code existant sans casser
- Creer LXC Debian 12 sur PVE02 (4 vCPU, 4 Go, 100 Go)
- Installer PostgreSQL 17 + config reseau
- Valider connexion depuis le dev local
- **Livrable** : Monorepo fonctionnel + LXC avec PostgreSQL accessible

Plans:
- [ ] (a planifier)

### Phase 9 — Schema BDD Universel
**Objectif** : Designer et migrer vers un schema couvrant tous les types parlementaires.
- Schema unifie : acteurs, organes, legislatures, seances, interventions, questions, amendements, scrutins, votes, dossiers_legislatifs, commissions_cr, tags
- Migrations Drizzle (5 tables -> ~15 tables)
- Migrer les 2 479 interventions existantes
- Index FTS francais sur tous les champs texte
- **Livrable** : Schema deploye sur LXC, donnees existantes migrees

Plans:
- [ ] (a planifier)

### Phase 10 — Ingestion Acteurs & Organes
**Objectif** : Peupler la base avec tous les acteurs et organes parlementaires.
- Source : Tricoteuses (@tricoteuses/assemblee) + data.senat.fr
- Deputes XVIIe (AN) + Senateurs (Senat)
- Ministres (gouvernement en exercice)
- Organes : commissions permanentes, groupes politiques, delegations
- Matching/dedup avec les 618 deputes existants
- **Livrable** : ~1 000 acteurs + ~200 organes en base

Plans:
- [ ] (a planifier)

### Phase 11 — Ingestion Debats (CRI)
**Objectif** : Ingerer toutes les seances publiques AN + Senat de la XVIIe legislature.
- Source AN : data.assemblee-nationale.fr (XML bulk) ou Tricoteuses
- Source Senat : data.senat.fr (XML/SQL dump CRI)
- Toutes les seances XVIIe (~200-300 AN + ~200 Senat)
- Parsing XML, rattachement orateurs, normalisation
- Tagging thematique etendu
- **Livrable** : ~400 debats, ~200K interventions en base

Plans:
- [ ] (a planifier)

### Phase 12 — Ingestion Questions
**Objectif** : Ingerer les questions parlementaires et reponses du gouvernement.
- QAG : Questions au Gouvernement (mardi/mercredi)
- Questions ecrites + reponses du Gouvernement
- QOSD : Questions orales sans debat
- Sources : data.assemblee-nationale.fr + data.senat.fr
- **Livrable** : ~20K questions en base

Plans:
- [ ] (a planifier)

### Phase 13 — Ingestion Amendements & Votes
**Objectif** : Ingerer les amendements et scrutins par parlementaire.
- Amendements : auteur, texte, expose des motifs, sort (adopte/rejete/retire)
- Scrutins : type, resultat, position de chaque parlementaire
- Sources : data.assemblee-nationale.fr (XML/JSON)
- **Livrable** : ~50K amendements, ~500 scrutins en base

Plans:
- [ ] (a planifier)

### Phase 14 — Ingestion Dossiers & Commissions
**Objectif** : Ingerer les parcours legislatifs et CR commissions.
- Dossiers legislatifs : titre, etapes de la navette, texte adopte
- CR commissions : comptes rendus des commissions permanentes
- Sources : data.assemblee-nationale.fr + data.senat.fr
- **Livrable** : ~200 dossiers, ~300 CR en base

Plans:
- [ ] (a planifier)

### Phase 15 — API REST Universelle
**Objectif** : Refonte de l'API pour couvrir tous les types de donnees.
- Refonte des endpoints existants + nouveaux
- /api/debates, /api/questions, /api/amendments, /api/votes, /api/dossiers
- Filtres avances (chambre, groupe, theme, date, texte)
- FTS enrichi (recherche cross-types)
- Documentation OpenAPI / Swagger
- **Livrable** : API documentee couvrant toutes les donnees

Plans:
- [ ] (a planifier)

### Phase 16 — Adaptation Frontend Poliscope
**Objectif** : Adapter l'interface pour exploiter toutes les nouvelles donnees.
- Nouvelles pages : Senat, votes/scrutins, amendements, dossiers
- Navigation bicamerale (AN <-> Senat)
- Recherche unifiee cross-types
- Tableaux de bord par parlementaire enrichis
- **Livrable** : Frontend complet exploitant la BDD universelle

Plans:
- [ ] (a planifier)

### Phase 17 — Deploiement & Ops
**Objectif** : Deployer sur LXC et mettre en place l'operationnel.
- Deploy API + BDD sur LXC PVE02
- Strategie backup PostgreSQL (pg_dump cron)
- Cron hebdo pour refresh donnees DILA/AN/Senat
- Monitoring basique (health check, disk usage)
- **Livrable** : App en production sur LXC, donnees auto-refreshed

Plans:
- [ ] (a planifier)
