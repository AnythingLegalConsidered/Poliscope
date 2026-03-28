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

### Phase 7 — Polish & Lancement
**Objectif** : Finitions avant mise en ligne.
- SEO (meta tags, sitemap, structured data)
- Performance (lazy loading, caching)
- Page "A propos" + mentions legales
- Tests E2E sur les parcours principaux
- **Livrable** : App prete pour un hebergement public
