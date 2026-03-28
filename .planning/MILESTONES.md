# Poliscope — Milestones

## v1.0 — MVP Debats AN (en cours)

**Periode** : 2026-03-27 — en cours
**Phases** : 1-7 (7 phases, ~16 plans)
**Status** : Phase 7 en cours (plan 01/02 complete)

**Ce qui a ete livre :**
- Infrastructure Nuxt 4 + PostgreSQL 17 + Drizzle ORM + Docker Compose
- Pipeline Python ingestion (DILA CRI + nosdeputes.fr) : 5 debats, 2 479 interventions, 618 deputes
- Tagging thematique automatique (12 tags, 787 assignments)
- API REST : 6 endpoints GET (debates, deputies, search, health)
- Full-text search PostgreSQL (francais, ts_rank, ts_headline, websearch_to_tsquery)
- UI complete : home (infinite scroll), thread debat, liste deputes, profil depute, recherche
- Design system Marbre & Bronze (Cinzel + Inter, 11 couleurs groupes politiques)
- SEO (useSeoMeta, @nuxtjs/sitemap, robots.txt, routeRules caching)
- Pages about + mentions legales

**Restant :**
- Phase 7 plan 02 : Tests E2E Playwright

**Decisions cles :**
- DILA CRI XML > nosdeputes.fr (XVIIe vide sur nosdeputes)
- Drizzle + raw SQL pour FTS
- whitespace-pre-wrap (XSS-safe)
- URL sync unidirectionnel (pas de watch route.query)

---

## v2.0 — Base de Donnees Parlementaire Universelle (planifie)

**Debut prevu** : apres completion v1.0
**Phases** : 8-17 (10 phases)

**Objectif :** BDD PostgreSQL complete de toutes les donnees parlementaires francaises (XVIIe legislature), hebergee sur LXC dedie PVE02, exposee via API REST universelle.

**Scope :**
- Niveau 3 complet : CRI, QAG, Questions ecrites, QOSD, Amendements, Votes, Dossiers, Commissions
- XVIIe legislature (2024-now)
- AN + Senat
- ~10-15 Go de donnees

**Architecture :**
- Monorepo (packages/api + packages/web)
- LXC Debian 12 sur PVE02 (4 vCPU, 4 Go RAM, 100 Go disk)
