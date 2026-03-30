# Poliscope — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Permettre a n'importe qui de chercher et lire ce qu'un parlementaire a dit sur n'importe quel sujet, en quelques clics.
**Current focus:** Phase 9 — Schema BDD Universel

## Current Position

- **Milestone** : 2 — Base de Donnees Parlementaire Universelle
- **Phase** : 10 — Ingestion Acteurs & Organes — COMPLETE (gap closure done)
- **Plan** : 3/3 — DONE
- **Status** : Phase 10 fully complete — 925 actors + 41 organs + 1311 actor_organs memberships
- **Last activity** : 2026-03-30 — Completed 10-03 gap closure (actor_organs table + AN memberships)

Progress: Milestone 1 [███████████████████] 17/17 plans DONE | Milestone 2 [████████░░░░░░░] 8/17 plans

## Accumulated Context

### Key Decisions (Milestone 2)

| Decision | Rationale |
|----------|-----------|
| Monorepo: packages/shared + packages/ingestion + packages/web | Types partages, scripts Python separes, Nuxt reste racine logique |
| Garder server/ dans Nuxt (pas Hono standalone) | Couplage auto-imports H3 — zero benefice a extraire pour un seul client |
| systemd timers (pas node-cron) | Ingestion Python independante du process Node; Persistent=true gere les runs manques |
| Cross-reference table avant toute autre ingestion | Previent la corruption silencieuse de FK entre sources (PA vs DILA vs slug vs Senat) |
| stored search_vector tsvector (pas functional index) | FTS cross-type scalable — functional index force row rechecks a >50K lignes |
| Questions/Amendements/Dossiers -> v3 | Scope raisonnable pour v2 ; votes sont la priorite citoyenne #1 |
| Votes ingeres en phase 12 (avant API/UI) | Data confidence avant exposition endpoints ; votes = attente principale |

### Key Decisions (Phase 10 — Plan 03)

| Decision | Rationale |
|----------|-----------|
| actor_organs UNIQUE on (actor_id, organ_id) | Deduplicates multiple mandats per pair — 1422 source rows -> 1311 via ON CONFLICT DO UPDATE |
| psycopg3 binary protocol: decode bytes on FK lookup | psycopg3 v3.3.2 returns text as bytes in binary mode — _decode() helper, no global conn change |
| Senat memberships deferred | senateurs.json has no membership dates — incomplete data worse than none; documented as known limitation |

### Key Decisions (Phase 10 — Plan 02)

| Decision | Rationale |
|----------|-----------|
| Filter AN organs to GP/COMPER/DELEG only | Skip meta-organs (ASSEMBLEE, BUREAU, OFFPAR) not useful for actor-organ queries |
| SENAT_ prefix for Senat organ official_ids | Prevent collision with AN PO IDs; slug-based for groups ensures stable IDs |
| political_group resolution via single SQL UPDATE | One UPDATE resolves all 577 PO refs — simpler than in-Python lookup |

### Key Decisions (Phase 10 — Plan 01)

| Decision | Rationale |
|----------|-----------|
| political_group pour AN stocke PO organeRef (pas le nom) | GP mandate contient un organeRef (ex: "PO834720") — resolu en nom lisible quand les organes sont ingeres en Plan 02 |
| legislature=None pour senateurs | Le Senat n'a pas de numerotation de legislature discrete (contrairement a l'AN) |
| GRANT ALL sur tables postgres-owned a l'utilisateur poliscope | Tables creees par postgres dans migration 0002 — poliscope user avait besoin de droits explicites pour INSERT |

### Key Decisions (Phase 9 — Plan 02)

| Decision | Rationale |
|----------|-----------|
| crossReferences: sourceType + sourceId (not per-source columns) | Ajout d'une nouvelle source = nouvelle ligne, pas de schema change |
| organs.parentOrganId sans FK constraint | Self-ref FK cause des problemes d'insert circulaire — resolu au niveau applicatif |
| questions et amendments: schema-only (pas d'ingestion) | Scope v2 raisonnable — votes sont la priorite #1, QAG/amendements -> v3 |

### Key Decisions (Phase 9 — Plan 01)

| Decision | Rationale |
|----------|-----------|
| drizzle-kit --custom + snapshot manual update | --custom crée SQL vide + snapshot copie; mise a jour manuelle evite DROP/CREATE lors du prochain generate |
| Snapshot GENERATED ALWAYS AS avec noms qualifies (actors.full_name) | drizzle-kit génère les expressions avec table.column — doit matcher exactement pour eviter le delta |
| API response fields (deputyId, deputyName) inchanges | Backward compat frontend — seuls les refs Drizzle internes changent; API contract stable jusqu'en Phase 13 |

### Key Decisions (Phase 8)

| Decision | Rationale |
|----------|-----------|
| shared exports TypeScript source directement (pas de build) | Vite resout .ts dans monorepo — pas besoin de transpiler shared |
| shamefully-hoist=true dans .npmrc | Nuxt auto-imports scanne node_modules heuristiquement — hoisting requis |
| Import shared: import * as schema from 'shared/schema' | Via exports field + workspace:* — pas d'import relatif cross-package |
| Python config.py .env path: 3 niveaux (packages/ingestion/scripts/ -> root) | Structure monorepo impose 3 niveaux vs 1 avant |
| community.proxmox.proxmox (not community.general.proxmox) | community.general.proxmox est deprecie — supprime en community.general 15.0.0 |
| api_password auth par defaut, token en commentaire | Plus simple pour premier run ; token mieux documente pour suite |
| scram-sha-256 dans pg_hba.conf | Default PG17 — ne pas downgrader en md5 |
| UFW default deny + allow explicite 22/5432/3000 LAN | Securite minimale — LXC expose uniquement ce qui est necessaire |

### Blockers / Risks

- **Phase 10** : URL Tricoteuses a valider (migration Framagit -> git.en-root.org, retourne 403 en research)
- **Phase 11** : Format XML Senat (Akoma Ntoso) non valide — echantillonner 2-3 CR recents avant implementation
- **Phase 12** : Schema Dosleg dump PostgreSQL 8.4 non inspecte — tester compatibilite avec PG17 avant ingestion
- **Phase 13** : Compatibilite @scalar/nuxt avec Nuxt 4 a confirmer (30 min check)
- **Schema** : ~~Rename `deputies -> actors`~~ DONE — migration appliquee avec succes (618 actors, zero perte)

### Pending Todos

None.

## Session Continuity

- **Last session** : 2026-03-30
- **Stopped at** : Phase 10 gap closure complete — 1311 actor_organs rows, 8-step pipeline
- **Resume** : Phase 11 — Ingestion Debats & Interventions (XML AN + Senat)

## History

- 2026-03-30 : Completed 10-03 — actor_organs table (migration 0004), 1311 AN memberships from AMO10 mandats, run_all.py 8-step pipeline, Senat limitation documented
- 2026-03-28 : Completed 10-02 — 24 AN organs + 17 Senat organs ingested, 577 actors' political_group resolved from PO ref to name, run_all.py updated to 7-step pipeline
- 2026-03-28 : Completed 10-01 — 577 AN deputies + 348 senators ingested (open data ZIP + senat.fr API), migration 0003 unique constraint applied, GRANT permissions on postgres-owned tables
- 2026-03-28 : Completed 09-03 gap closure — fix idx_interventions_fts name, apply migrations 0001+0002 to live DB (psql SSH), verified 618 actors + 2479 interventions + FTS indexes + API endpoints
- 2026-03-28 : Completed 09-02 — 7 new tables (legislatures, organs, scrutins, votes, questions, amendments, cross_references), debates.chamber, additive migration 0002 (zero DROP TABLE)
- 2026-03-28 : Completed 09-01 — rename deputies->actors (safe migration), stored tsvector FTS columns, all 6 API routes -> shared/schema
- 2026-03-28 : Phase 8 complete — verification PASSED (7/7 must-haves). LXC 200 poliscope-db provisioned (PG17.9), monorepo pnpm, E2E 11/11

- 2026-03-28 : Completed 08-01 — pnpm monorepo: packages/shared + packages/web + packages/ingestion, pnpm build passes
- 2026-03-28 : Completed 08-02 (partial) — Ansible playbook LXC + PG17 cree, checkpoint Task 2 (execution manuelle)
- 2026-03-28 : Milestone 2 roadmap cree — 8 phases (8-15), 35 requirements mappes, STATE.md mis a jour
- 2026-03-28 : Milestone 1 complete — Phase 7 verification PASSED (14/14 must-haves)
- 2026-03-28 : Completed 07-02 — Playwright E2E suite: 11 tests across 4 spec files
- 2026-03-28 : Completed 07-01 — SEO + sitemap + routeRules caching + about/legal pages
- 2026-03-28 : Phase 6 complete — verification PASSED (10/10 must-haves)
- 2026-03-28 : Completed 06-02 — Global header search bar + NuxtLink fix
- 2026-03-28 : Completed 06-01 — /search page with FTS highlights + infinite scroll + URL sync
- 2026-03-28 : Phase 5 complete — verification PASSED (13/13 must-haves)
- 2026-03-28 : Phase 4 complete — verification PASSED (11/11 must-haves)
- 2026-03-27 : Phase 3 complete — API REST 6 endpoints
- 2026-03-27 : Phase 2 complete — 5 debats, 2 479 interventions, 618 deputes, 12 tags
- 2026-03-27 : Phase 1 complete — Nuxt 4 + Docker Compose + Drizzle
