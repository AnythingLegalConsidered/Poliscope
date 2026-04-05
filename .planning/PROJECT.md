# Poliscope

## What This Is

Explorateur de debats parlementaires francais bicameral (Assemblee Nationale + Senat). Rend les interventions, scrutins et votes accessibles dans une interface moderne type "thread Twitter", avec recherche full-text cross-type. Deploye en production sur LXC PVE02. Destine aux citoyens qui veulent comprendre ce que disent et votent leurs elus.

## Core Value

Permettre a n'importe qui de chercher et lire ce qu'un parlementaire a dit sur n'importe quel sujet, en quelques clics.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — Milestone 1 -->

- [x] Ingestion des debats AN depuis DILA (CRI XML) — v1.0
- [x] Ingestion des deputes depuis nosdeputes.fr — v1.0
- [x] Tagging thematique automatique (12 tags) — v1.0
- [x] API paginee debates, deputies, search — v1.0
- [x] Full-text search PostgreSQL (francais, ts_rank, ts_headline) — v1.0
- [x] Page d'accueil avec liste des debats (infinite scroll) — v1.0
- [x] Page thread debat (interventions en fil vertical) — v1.0
- [x] Composants InterventionCard, DebateCard, GroupBadge — v1.0
- [x] Design system Marbre & Bronze (Cinzel + Inter) — v1.0
- [x] Liste deputes avec recherche et filtre groupe — v1.0
- [x] Profil depute avec stats, tag filter, navigation bidirectionnelle — v1.0
- [x] Page recherche avec URL sync, highlighting, filtres — v1.0
- [x] Barre de recherche globale dans le header — v1.0
- [x] SEO (useSeoMeta, sitemap, robots.txt, routeRules caching) — v1.0
- [x] Pages about + mentions legales — v1.0

<!-- Shipped and confirmed valuable — Milestone 2 -->

- [x] Monorepo pnpm (packages/shared + packages/web + packages/ingestion) — v2.0
- [x] LXC Debian 12 dedie sur PVE02 (PG17, PM2, nginx) — v2.0
- [x] Schema BDD universel (acteurs, organes, scrutins, votes, cross_references) — v2.0
- [x] Migration deputies → actors sans perte de donnees — v2.0
- [x] Ingestion acteurs bicameraux : 577 deputes AN + 348 senateurs — v2.0
- [x] Ingestion organes : 41 organes AN + Senat, 1311 memberships — v2.0
- [x] Ingestion debats CRI AN + Senat (XVIIe) : ~500 seances, ~300k interventions — v2.0
- [x] Ingestion scrutins/votes : 7062 scrutins, 1.3M votes (AN + Senat) — v2.0
- [x] API REST universelle : votes, filtre chambre, FTS cross-type, Swagger /api/docs — v2.0
- [x] Frontend bicameral : pages scrutins, navigation AN/Senat, badge chambre — v2.0
- [x] Deploiement production : backup pg_dump quotidien, refresh hebdo systemd timers — v2.0
- [x] Sitemap scrutins + voteStats profil + badge chambre DeputyCard — v2.0

### Active

<!-- Next milestone scope — TBD -->

(Aucun — prochain milestone a definir)

### Out of Scope

- Legislatures anterieures a la XVIIe — Commencer avec les donnees les plus propres, etendre plus tard
- Parlement europeen — Perimetre France uniquement
- Authentification utilisateur — Donnees publiques, pas de comptes necessaires
- IA / NLP avance — Pas de resume automatique ou analyse de sentiment
- Application mobile — Web-first, responsive suffit
- Questions (QAG, ecrites, QOSD) — Deferred to v3
- Amendements (auteur, contenu, sort) — Deferred to v3
- Dossiers legislatifs (parcours navette) — Deferred to v3
- CR Commissions — Deferred to v3

## Context

**Current state (v2.0 shipped):**
- Codebase: 6,402 LOC TypeScript/Vue + 3,748 LOC Python + 243 LOC shared
- Tech stack: Nuxt 4 + PostgreSQL 17 + Drizzle ORM + pnpm monorepo
- Infra: LXC Debian 12 sur PVE02 (4 vCPU, 4 Go RAM, 100 Go disk)
- Donnees: 925 acteurs, 41 organes, ~500 seances, ~300k interventions, 7062 scrutins, 1.3M votes
- Production: http://192.168.2.200, backup quotidien 74 MB, refresh hebdo automatique
- Sources: DILA CRI XML (AN), cri.zip (Senat), data.assemblee-nationale.fr, senat.fr API, Dosleg dump

**Known tech debt:**
- Senat organ membership dates NULL (source limitation)
- ~10% Senat votes unmatched (inactive senators)
- ingest_deputies.py kept as dead code (Step 6 removed from pipeline)
- No formal VERIFICATION.md for Phase 15

## Constraints

- **Tech stack** : Nuxt 4 + PostgreSQL 17 + Drizzle — valide en v1.0 et v2.0
- **Infra** : LXC sur PVE02, Debian 12, 4 vCPU / 4 Go RAM / 100 Go disk
- **Architecture** : Monorepo pnpm (packages/shared + packages/web + packages/ingestion)
- **Couverture** : XVIIe legislature uniquement (2024-now)
- **Sources** : Open data uniquement (Licence Ouverte)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DILA CRI XML comme source debats | nosdeputes.fr vide pour XVIIe, DILA a les archives | ✓ Good |
| Drizzle ORM + raw SQL pour FTS | Drizzle ne supporte pas ts_rank/ts_headline nativement | ✓ Good |
| whitespace-pre-wrap (pas v-html) | XSS-safe pour le contenu parlementaire | ✓ Good |
| Monorepo pnpm (3 packages) | Dev solo, deploiement coordonne, partage types via shared | ✓ Good |
| LXC Debian 12 sur PVE02 | Infrastructure existante, 4 vCPU/4Go/100Go suffisant | ✓ Good |
| Cross-reference table avant ingestion | Previent corruption FK entre sources (PA, DILA, Senat) | ✓ Good |
| stored search_vector tsvector | Scalable vs functional index, performant a >50K lignes | ✓ Good |
| Dosleg text parsing (pas pg_restore) | PG 8.4 dump incompatible PG 17, COPY blocks parseable | ✓ Good |
| httpx.stream() pour cri.zip Senat | 510 MB ZIP — evite OOM sur LXC 4 Go RAM | ✓ Good |
| SQL UNION ALL pour FTS cross-type | count(*) OVER() sur outer query, branches conditionnelles | ✓ Good |
| systemd timers (pas node-cron) | Python independant de Node, Persistent=true gere les runs manques | ✓ Good |
| Questions/Amendements/Dossiers → v3 | Scope raisonnable, votes = priorite citoyenne #1 | ✓ Good |
| XVIIe legislature seulement | Donnees les plus propres, scope raisonnable | ✓ Good |

---
*Last updated: 2026-04-05 after v2.0 milestone*
