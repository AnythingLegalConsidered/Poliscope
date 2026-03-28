# Poliscope

## What This Is

Explorateur de debats parlementaires francais. Rend les interventions de l'Assemblee Nationale et du Senat accessibles dans une interface moderne type "thread Twitter". Destine aux citoyens qui veulent comprendre ce que disent leurs elus.

## Core Value

Permettre a n'importe qui de chercher et lire ce qu'un parlementaire a dit sur n'importe quel sujet, en quelques clics.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — Milestone 1 -->

- [x] Ingestion des debats AN depuis DILA (CRI XML) — Phase 2
- [x] Ingestion des deputes depuis nosdeputes.fr — Phase 2
- [x] Tagging thematique automatique (12 tags) — Phase 2
- [x] API paginee debates, deputies, search — Phase 3
- [x] Full-text search PostgreSQL (francais, ts_rank, ts_headline) — Phase 3
- [x] Page d'accueil avec liste des debats (infinite scroll) — Phase 4
- [x] Page thread debat (interventions en fil vertical) — Phase 4
- [x] Composants InterventionCard, DebateCard, GroupBadge — Phase 4
- [x] Design system Marbre & Bronze (Cinzel + Inter) — Phase 4
- [x] Liste deputes avec recherche et filtre groupe — Phase 5
- [x] Profil depute avec stats, tag filter, navigation bidirectionnelle — Phase 5
- [x] Page recherche avec URL sync, highlighting, filtres — Phase 6
- [x] Barre de recherche globale dans le header — Phase 6
- [x] SEO (useSeoMeta, sitemap, robots.txt, routeRules caching) — Phase 7
- [x] Pages about + mentions legales — Phase 7

### Active

<!-- Current scope — Milestone 2: Base de Donnees Parlementaire Universelle -->

- [ ] Restructuration monorepo (packages/api + packages/web)
- [ ] LXC Debian 12 dedie sur PVE02 (4 vCPU, 4 Go RAM, 100 Go)
- [ ] Schema BDD universel (~15 tables, tous types parlementaires)
- [ ] Ingestion acteurs : deputes, senateurs, ministres
- [ ] Ingestion organes : commissions, groupes politiques
- [ ] Ingestion debats CRI AN + Senat (XVIIe legislature complete)
- [ ] Ingestion questions (QAG, questions ecrites, QOSD)
- [ ] Ingestion amendements (auteur, contenu, sort)
- [ ] Ingestion votes/scrutins (position par parlementaire)
- [ ] Ingestion dossiers legislatifs (parcours navette)
- [ ] Ingestion CR commissions
- [ ] API REST universelle avec documentation OpenAPI
- [ ] Adaptation frontend (pages Senat, votes, amendements)
- [ ] Deploiement sur LXC + backup + cron refresh

### Out of Scope

- Legislatures anterieures a la XVIIe — Commencer avec les donnees les plus propres, etendre plus tard
- Parlement europeen — Perimetre France uniquement pour l'instant
- Authentification utilisateur — Donnees publiques, pas de comptes necessaires
- IA / NLP avance — Pas de résume automatique ou analyse de sentiment pour ce milestone
- Application mobile — Web-first, responsive suffit

## Context

- Donnees sources : DILA (JO), data.assemblee-nationale.fr, data.senat.fr, nosdeputes.fr/nossenateurs.fr, Tricoteuses
- 5 debats actuellement ingeres (2 479 interventions, 618 deputes)
- Volume cible : ~10-15 Go pour toutes les donnees XVIIe legislature
- Pipeline Python existant (ingest_deputies.py, ingest_debates.py, tag_interventions.py)
- Infrastructure : PVE02 (Proxmox VE) disponible pour hebergement LXC

## Constraints

- **Tech stack** : Nuxt 4 + PostgreSQL 17 + Drizzle — valide en Milestone 1, on continue
- **Infra** : LXC sur PVE02, Debian 12, 4 vCPU / 4 Go RAM / 100 Go disk
- **Architecture** : Monorepo (packages/api + packages/web)
- **Couverture** : XVIIe legislature uniquement (2024-now)
- **Sources** : Open data uniquement (Licence Ouverte)

## Current Milestone: v2.0 Base de Donnees Parlementaire Universelle

**Goal:** Construire une BDD PostgreSQL complete hebergeant toutes les donnees parlementaires francaises (XVIIe legislature), deployee sur LXC dedie, avec API REST universelle et frontend adapte.

**Target features:**
- Schema BDD universel (CRI, QAG, Questions, Amendements, Votes, Dossiers, Commissions)
- Pipelines ingestion multi-sources (Tricoteuses, data.senat.fr, DILA, data.assemblee-nationale.fr)
- API REST documentee (OpenAPI)
- Frontend adapte pour exploiter toutes les donnees
- Deploiement sur infrastructure dediee (LXC PVE02)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DILA CRI XML comme source debats | nosdeputes.fr vide pour XVIIe, DILA a les archives | ✓ Good |
| Drizzle ORM + raw SQL pour FTS | Drizzle ne supporte pas ts_rank/ts_headline nativement | ✓ Good |
| whitespace-pre-wrap (pas v-html) | XSS-safe pour le contenu parlementaire | ✓ Good |
| Monorepo (packages/api + web) | Dev solo, deploiement coordonne, partage types | — Pending |
| LXC Debian 12 sur PVE02 | Infrastructure existante, 4 vCPU/4Go/100Go suffisant | — Pending |
| Tricoteuses comme source primaire AN | Donnees nettoyees, pretes a l'emploi en TS | — Pending |
| XVIIe legislature seulement | Donnees les plus propres, scope raisonnable | — Pending |

---
*Last updated: 2026-03-28 after Milestone 2 initialization*
