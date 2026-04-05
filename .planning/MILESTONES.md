# Poliscope — Milestones

## v1.0 — MVP Debats AN (Shipped: 2026-03-28)

**Periode** : 2026-03-27 — 2026-03-28
**Phases** : 1-7 (7 phases, 17 plans)

**Ce qui a ete livre :**
- Infrastructure Nuxt 4 + PostgreSQL 17 + Drizzle ORM + Docker Compose
- Pipeline Python ingestion (DILA CRI + nosdeputes.fr) : 5 debats, 2 479 interventions, 618 deputes
- Tagging thematique automatique (12 tags, 787 assignments)
- API REST : 6 endpoints GET (debates, deputies, search, health)
- Full-text search PostgreSQL (francais, ts_rank, ts_headline, websearch_to_tsquery)
- UI complete : home (infinite scroll), thread debat, liste deputes, profil depute, recherche
- Design system Marbre & Bronze (Cinzel + Inter, 11 couleurs groupes politiques)
- SEO (useSeoMeta, @nuxtjs/sitemap, robots.txt, routeRules caching)
- Tests E2E Playwright (11 tests, 4 spec files)

**Decisions cles :**
- DILA CRI XML > nosdeputes.fr (XVIIe vide sur nosdeputes)
- Drizzle + raw SQL pour FTS
- whitespace-pre-wrap (XSS-safe)
- URL sync unidirectionnel (pas de watch route.query)

**Archive** : [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

---

## v2.0 — Base de Donnees Parlementaire Universelle (Shipped: 2026-04-05)

**Periode** : 2026-03-28 — 2026-04-05
**Phases** : 8-16 (9 phases, 22 plans)
**Commits** : 65 | **Files** : 172 modifies (+23,249 / -12,337 lines)
**Codebase** : 6,402 LOC TypeScript/Vue + 3,748 LOC Python + 243 LOC shared

**Ce qui a ete livre :**
- Monorepo pnpm (packages/shared + packages/web + packages/ingestion)
- LXC Debian 12 sur PVE02 avec PostgreSQL 17
- Schema BDD universel : acteurs, organes, legislatures, scrutins, votes, cross_references
- Migration deputies → actors sans perte (618 acteurs)
- Ingestion bicamerale : 925 acteurs (577 AN + 348 Senat), 41 organes, 1311 memberships
- Debats CRI AN + Senat : ~500 seances, ~300k interventions, tagging thematique
- Scrutins/Votes : 7062 scrutins, 1.3M votes (AN Scrutins.json.zip + Senat Dosleg SQL dump)
- API REST universelle : endpoints votes, filtre chambre, FTS cross-type, Swagger UI /api/docs
- Frontend bicameral : pages scrutins, navigation AN/Senat, badge chambre, search cross-type
- Deploiement production : PM2 + nginx sur LXC, backup pg_dump quotidien, refresh hebdo systemd timers
- Gap closure : legacy script retire, voteStats rendu, badge chambre, sitemap scrutins

**Decisions cles :**
- Cross-reference table avant toute ingestion (previent corruption FK)
- stored search_vector tsvector (scalable vs functional index)
- Dosleg text parsing (PG 8.4 dump incompatible PG 17)
- httpx.stream() pour cri.zip Senat (510 MB)
- SQL UNION ALL pour FTS cross-type
- systemd timers (pas node-cron) pour backup/refresh
- Questions/Amendements/Dossiers deferred → v3

**Archive** : [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)

---
