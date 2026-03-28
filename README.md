# Poliscope

Explorateur de debats parlementaires francais. Rend accessible les interventions de l'Assemblee Nationale et du Senat dans une interface moderne et lisible.

## Fonctionnalites

- **Debats en thread** -- Les seances publiques affichees comme des fils de conversation
- **Profils parlementaires** -- Fiche depute avec historique des interventions et stats thematiques
- **Recherche full-text** -- PostgreSQL FTS avec highlighting et filtres (theme, depute, chambre)
- **Navigation bicamerale** -- Assemblee Nationale + Senat (a venir)
- **Donnees ouvertes** -- Sources : DILA, data.assemblee-nationale.fr, data.senat.fr, Tricoteuses

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Frontend | Nuxt 4 (Vue 3, TypeScript strict) |
| Styling | Tailwind CSS v4 -- palette "Marbre & Bronze" (Cinzel + Inter) |
| Backend | API routes Nuxt (H3) |
| Base de donnees | PostgreSQL 17 + Drizzle ORM |
| Recherche | PostgreSQL FTS (francais, ts_rank, ts_headline) |
| Ingestion | Python 3.12 (pipelines DILA + nosdeputes.fr) |
| Tests E2E | Playwright |
| Deploy | Docker Compose / LXC Proxmox |

## Demarrage rapide

```bash
# Prerequis : Node.js 22+, Docker, Python 3.12+

# 1. Installer les dependances
pnpm install

# 2. Lancer PostgreSQL
docker compose up -d

# 3. Appliquer le schema
pnpm db:push

# 4. Ingerer les donnees
cd scripts && python run_all.py

# 5. Lancer le dev server
pnpm dev
# -> http://localhost:3000
```

## Structure du projet

```
poliscope/
  app/                    # Frontend Nuxt
    pages/                # Routes (/, /debates/[id], /deputies, /search)
    components/           # DebateCard, InterventionCard, DeputyCard, etc.
    layouts/              # Header sticky + footer
    utils/                # groupColors (11 groupes politiques)
    assets/css/           # Tailwind theme Marbre & Bronze
  server/
    api/                  # 6 endpoints GET (debates, deputies, search)
    db/                   # Schema Drizzle (5 tables)
    utils/                # DB singleton, pagination helper
  scripts/                # Pipeline Python (ingestion + tagging)
  .planning/              # Roadmap, state, plans GSD
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/debates` | Liste des seances (paginee) |
| `GET /api/debates/:id` | Thread complet d'un debat |
| `GET /api/deputies` | Liste des deputes (filtre groupe, recherche) |
| `GET /api/deputies/:id` | Profil + interventions + stats tags |
| `GET /api/search` | Recherche full-text avec filtres |
| `GET /api/health` | Health check |

## Donnees actuelles

- **5 debats** de la XVIIe legislature (source DILA CRI)
- **2 479 interventions** rattachees aux orateurs
- **618 deputes** (source nosdeputes.fr)
- **12 tags thematiques** (immigration, sante, economie, etc.)

## Roadmap

### Milestone 1 -- MVP Debats AN *(en cours)*

| Phase | Nom | Status |
|-------|-----|--------|
| 1 | Setup & Infrastructure | Done |
| 2 | Ingestion donnees AN | Done |
| 3 | API Backend | Done |
| 4 | UI Debats (Thread View) | Done |
| 5 | Profils Deputes | Done |
| 6 | Recherche & Filtres | Done |
| 7 | Polish & Lancement | En cours |

### Milestone 2 -- Base de Donnees Parlementaire Universelle *(planifie)*

Objectif : BDD PostgreSQL complete de toutes les donnees parlementaires francaises (XVIIe legislature), hebergee sur LXC dedie, exposee via API REST universelle.

| Phase | Nom | Scope |
|-------|-----|-------|
| 8 | Monorepo & Infra LXC | Restructuration monorepo, LXC Debian 12 sur Proxmox |
| 9 | Schema BDD Universel | ~15 tables couvrant tous les types parlementaires |
| 10 | Ingestion -- Acteurs & Organes | Deputes, senateurs, ministres, commissions, groupes |
| 11 | Ingestion -- Debats (CRI) | Seances publiques AN + Senat, XVIIe complete |
| 12 | Ingestion -- Questions | QAG, questions ecrites, QOSD |
| 13 | Ingestion -- Amendements & Votes | Amendements + scrutins par parlementaire |
| 14 | Ingestion -- Dossiers & Commissions | Parcours legislatifs + CR commissions |
| 15 | API REST Universelle | Endpoints tous types, filtres avances, OpenAPI |
| 16 | Adaptation Frontend | Nouvelles pages, navigation bicamerale, recherche enrichie |
| 17 | Deploiement & Ops | Deploy LXC, backups, cron refresh, monitoring |

**Donnees cibles** : ~10-15 Go | CRI, QAG, Questions, Amendements, Votes, Dossiers, Commissions

## Design

Palette **Marbre & Bronze** inspiree de l'esthetique parlementaire :
- `marble` (#FAF6F0) -- fond creme
- `bronze` (#A0744F) -- accent principal
- `ink` (#2A1F14) -- texte
- Typographie : Cinzel (titres) + Inter (corps)
- 11 couleurs de groupes politiques (LFI, RN, REN, LR, SOC, ECO, etc.)

## Licence

Projet personnel -- donnees parlementaires sous Licence Ouverte.
