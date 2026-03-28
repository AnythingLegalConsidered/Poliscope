# Project Research Summary

**Project:** Poliscope — Universal Parliamentary Database (BDD Parlementaire Universelle)
**Domain:** Civic tech / parliamentary data explorer — AN + Sénat bicameral coverage, XVIIe legislature
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

Poliscope is expanding from a working Milestone 1 product (AN debates + deputy profiles + FTS search) into a universal bicameral parliamentary database covering all major French parliamentary data types: votes, amendments, questions, dossiers législatifs, and Sénat coverage. The research shows this is a well-understood domain with validated demand — competitors like nosdeputes.fr, datan.fr, and pappers.fr demonstrate the feature set citizens expect, but each has significant gaps (nosdeputes stale on XVIIe, datan votes-only, lafabriquedelaloi abandoned). The primary architectural decision is to keep the Nuxt `server/` code in place rather than extracting a standalone API, and to reorganize into a pnpm monorepo with a `packages/shared` types package and a `packages/ingestion` Python package. This is the lowest-friction path for a solo developer.

The recommended build order is strict: actors ingestion must come first (it is the FK root for every other data type), then data ingestion pipelines in dependency order, then API layer extension, then frontend adaptation. The highest-value differentiators are unified actor pages (député + sénateur same UI), the dossier législatif avec navette timeline (no active competitor does this well), and cross-type full-text search. The REST API with OpenAPI docs is deferred to v2 since the citizen audience comes before the developer audience.

Three risks dominate: (1) deputy/senator ID mismatches across sources causing silent FK corruption — mitigated by building a cross-reference table before any non-DILA ingestion; (2) schema migration data loss — mitigated by incremental migration files and never using `drizzle-kit push` outside a clean local DB; (3) Nuxt module resolution breaking after monorepo restructure — mitigated by validating `nuxt build` (not just `nuxt dev`) immediately after moving files. All three risks are well-understood and preventable with the right discipline.

## Key Findings

### Recommended Stack

The existing stack (Nuxt 4, PostgreSQL 17, Drizzle ORM, Python 3.12, lxml, httpx) covers all new requirements without new runtime dependencies. The only new packages are Turborepo for build orchestration and `@scalar/nuxt` for OpenAPI docs generation. Scheduling is handled by systemd timers on the Debian 12 LXC — not node-cron — because ingestion is Python and must run independently of the Node.js process. LXC provisioning uses shell scripts with `pct`/`pvesh` — not Ansible or Terraform, which add overhead for a single container.

**Core technologies:**
- pnpm workspaces + Turborepo: monorepo linking with task caching — already using pnpm, Turborepo adds parallel builds in one config file
- Hono + @hono/zod-openapi: public REST API (v2) — TypeScript-first, zero-boilerplate OpenAPI generation; skip for Milestone 2 citizen-facing work
- systemd timers: cron scheduling for ingestion — Debian-native, Persistent=true handles missed runs, decoupled from Node process
- lxml iterparse: streaming XML parsing for large CRI/amendment archives — 2-20x faster than stdlib, already installed
- pct shell scripts: LXC provisioning on PVE02 — 20 lines, no external dependencies, runs once

**Critical version constraint:** @hono/zod-openapi requires zod ^3.x — zod v4 not yet supported as of 2026-03.

### Expected Features

The market gap Poliscope fills is unified AN + Sénat coverage with modern design and cross-type search. Acteurs ingestion is the non-negotiable root dependency — every other feature branches from it.

**Must have (table stakes — P1):**
- Universal schema + acteurs — député + sénateur in same actors table; root FK for everything
- Votes / scrutins (list + detail) — highest citizen demand; "did my deputy vote for X?" is the primary use case
- Amendements (list + detail) — pappers.fr and lafabriquedelaloi.fr validate demand
- Questions QAG + écrites — nosdeputes.fr validates demand; standard format
- Sénat CRI debates — symmetry with existing AN debates; same thread UI reusable
- Sénateurs profiles — mirrors deputy profiles; expected from a "universal" DB
- Updated deputy profiles — add votes + questions tabs from new data

**Should have (competitive — P2):**
- Dossier législatif avec navette timeline — killer feature; no active competitor does this well; HIGH complexity
- Cross-type full-text search — extends existing FTS infra to all new tables; depends on all pipelines complete
- Activity score per parlementaire — computed from all data types, more honest than vote-only competitors
- CR Commissions — underserved by all competitors; low effort once schema exists

**Defer (v2+ — P3):**
- REST API + OpenAPI docs — developer audience secondary; defer until data is stable
- Bicameral vote comparison — requires dossiers linkage + both chambers' scrutins
- RSS feeds — stateless subscription, low complexity but low priority
- Previous legislatures (XVIe) — only after XVIIe is complete

**Anti-features to avoid:** Email alerts (auth + GDPR), gamified activity scores (methodological controversy), AI summaries (hallucination risk in political context), real-time live sessions (WebSockets complexity + DILA delays).

### Architecture Approach

The architecture stays Nuxt-monolithic with shared packages for types only. The current `server/` H3 handlers are tightly coupled to Nuxt's auto-imports (`defineEventHandler`, `useRuntimeConfig`) — extracting to a standalone server would require rewiring all that plumbing for zero benefit since there is no other client. The target structure is: `packages/shared` (TypeScript types + Zod schemas), `packages/ingestion` (Python scripts reorganized by source), and the Nuxt app remains at root as `packages/web`. Schema splits into domain files (actors, debates, legislative). Ingestion dependency order is strict and must be respected.

**Major components:**
1. `packages/shared` — TypeScript interfaces (actors, debates, legislative, api) shared between web server and future API; no runtime logic
2. `packages/web/server/` — H3 event handlers extended with chamber filter + new endpoints (questions, amendments, votes, dossiers, organes); schema split into domain files
3. `packages/ingestion/` — Python scripts reorganized by source (an/, senat/, common/); orchestrator.py sequences them in dependency order; systemd timers schedule runs
4. PostgreSQL 17 (LXC PVE02) — single database, ~15 tables; actors table replaces deputies; sessions replaces debates

**Key patterns:**
- Additive-first schema migration: rename tables first (single migration), add tables second (safe), backfill third, FTS indexes CONCURRENTLY last
- Denormalized current group on actors table — avoids expensive joins on every list query
- Staging container for Senate SQL dumps — never pipe dumps directly into production DB
- `ingestion_warnings` table — log unmatched actors rather than silently discarding them

### Critical Pitfalls

1. **Monorepo breaks Nuxt build** — Nuxt's Vite bundler may fail to resolve workspace-local packages. Prevention: add shared packages to `vite.optimizeDeps.include` or `build.transpile`; never use `shamefully-hoist`; validate `nuxt build` (not just `nuxt dev`) immediately after any file move.

2. **Schema migration data loss** — Using `drizzle-kit push` on a shared DB, or a single mega-migration, risks silent data loss or blocking DDL. Prevention: incremental migration files (one per logical change), two-step NOT NULL additions, `CREATE INDEX CONCURRENTLY` in separate migration, always test on a prod DB snapshot first.

3. **Deputy/Senator ID mismatch (silent FK corruption)** — Each source uses a different ID scheme (PA prefix, numeric DILA ID, slugs, Sénat LA/PO IDs). Name-matching silently produces false positives. Prevention: build a cross-reference table mapping all source IDs to canonical PA IDs before ingesting any non-DILA source; log unmatched records to `ingestion_warnings`; reject Sénat IDs on AN actors.

4. **TAZ archive format variations** — DILA `.taz` files use LZW compression and vary in structure across years. Prevention: probe archive structure before assuming double-tar layout; test against archives from 2019, 2021, 2023, 2024, 2025; log exact errors on failure.

5. **Cross-type FTS noise at scale** — UNION ALL across 5 tables degrades non-linearly beyond 50K records; `to_tsvector()` functional index without stored column forces row rechecks. Prevention: stored `search_vector tsvector` column updated by trigger on each table; materialized search view for cross-type queries; benchmark with EXPLAIN ANALYZE before declaring done.

## Implications for Roadmap

The ARCHITECTURE.md phase numbering (8-17) reflects that Milestones 1-7 are already complete. The roadmap should treat these as absolute phase numbers continuing from the existing plan.

### Phase 8: Monorepo Restructure
**Rationale:** Everything downstream requires the monorepo to be in place — shared types can't be extracted, Python scripts can't be reorganized, and workspace dependencies can't be linked without this foundation.
**Delivers:** pnpm-workspace.yaml, packages/shared TypeScript types, packages/ingestion skeleton, Nuxt app relocated to packages/web
**Avoids:** Nuxt module resolution pitfall — validate `nuxt build` before declaring phase complete
**Research flag:** Standard pattern — well-documented in Nuxt + pnpm docs; no phase research needed. But build the validation checklist into the phase plan.

### Phase 9: Schema Migration
**Rationale:** All ingestion pipelines require the new tables to exist. Must happen before any data can be written.
**Delivers:** actors table (replaces deputies + adds senators), sessions with chamber column, new tables: mandates, organes, questions, amendments, scrutins, votes, dossiers, commission_cr
**Avoids:** Migration data loss pitfall — split into 4 incremental migration files (rename, add tables, backfill, indexes)
**Research flag:** Standard pattern — Drizzle migration docs are authoritative. Focus phase plan on the exact migration sequence.

### Phase 10: Actors + Organes Ingestion
**Rationale:** Actors is the FK root — every other pipeline fails without it. Must complete before phases 11-14.
**Delivers:** All AN deputies + senators + ministers in unified actors table; organes (commissions, groupes); mandates (membership history); cross-reference ID table (PA ↔ DILA numeric ↔ slug)
**Avoids:** Deputy ID mismatch pitfall — build the cross-reference table HERE, before any other ingestion starts
**Research flag:** Tricoteuses source URL needs validation (Framagit → git.en-root.org migration); nossenateurs.fr JSON API format needs sampling. Recommend brief phase research on these two sources only.

### Phase 11: CRI Debates Ingestion (AN + Sénat)
**Rationale:** AN CRI is the existing proven pipeline (refactor only). Sénat CRI depends on actors (phase 10). Both feed interventions which feed tag pipeline.
**Delivers:** AN CRI refactored to new actors table; Sénat CRI new parser; all debates in sessions table with chamber column; intervention tags updated
**Avoids:** TAZ archive format pitfall — test against 5 years of archives, not just latest
**Research flag:** Sénat CRI XML format (Akoma Ntoso) needs research before implementation — structure differs significantly from DILA format.

### Phase 12: Questions Ingestion
**Rationale:** Only depends on actors (phase 10), not on debates (phase 11) — can start in parallel with phase 11 if capacity allows.
**Delivers:** QAG + questions écrites + QOSD in questions table, linked to actors
**Avoids:** nosdeputes.fr API empty for legislature 17 — use official AN open data XML as primary source
**Research flag:** Standard pattern — AN open data XML format for questions is documented. No phase research needed.

### Phase 13: Amendments + Votes Ingestion
**Rationale:** Depends on actors (10) and sessions (11) for scrutin→session FK. Senate sources require staging container pattern.
**Delivers:** AN amendments from data.assemblee-nationale.fr ZIP; Senate amendments from Ameli PostgreSQL dump (via staging); AN votes from Scrutins.json.zip; Senate votes from Dosleg dump (via staging)
**Avoids:** Senate SQL dump pitfall — always use staging container, never pipe dumps into production
**Research flag:** Senate Ameli and Dosleg dump schemas need sampling before ingestion script is written — format is PostgreSQL 8.4-era. Recommend phase research on these two dump formats.

### Phase 14: Dossiers + Commission CR
**Rationale:** Dossiers are the linking layer that contextualizes everything (votes, amendments, CRI per legislative step). Commission CR depends on organes (10) and sessions (11).
**Delivers:** Dossiers législatifs with etapes JSON; commission_cr linked to organes; dossier FKs backfilled into amendments and sessions tables
**Avoids:** Dossier complexity — the navette timeline is the killer feature but is data-dependent; build the data layer first, the UI in phase 16
**Research flag:** Dossier data format from data.assemblee-nationale.fr needs sampling — multiple formats (JSON, XML, Akoma Ntoso) documented. Recommend brief phase research.

### Phase 15: Universal REST API
**Rationale:** Requires all data tables populated (phases 9-14). API layer extension before frontend prevents frontend from consuming unstable endpoints.
**Delivers:** All new endpoints (actors, questions, amendments, votes, dossiers, organes); existing endpoints updated (chamber filter, deputies→actors alias); cross-type FTS extended; @scalar/nuxt for OpenAPI docs
**Avoids:** Cross-type FTS noise pitfall — design stored search_vector columns + materialized view BEFORE writing the search endpoint
**Research flag:** @scalar/nuxt integration pattern is newer — validate against current Nuxt 4 before implementing. 30-minute research check recommended.

### Phase 16: Frontend Adaptation
**Rationale:** Requires phase 15 (stable API). Frontend builds on top of all data now available.
**Delivers:** Updated deputy profiles (votes + questions tabs); sénateurs profiles; votes list + detail pages; amendments list + detail pages; dossier législatif page with navette timeline; cross-type search UI with type facets; activity score on actor profiles
**Avoids:** UX pitfall — always show type_badge on mixed search results; always default-filter to legislature=17
**Research flag:** Navette timeline Vue component — no established component library covers this. Needs custom implementation planning. Standard UX pattern research recommended.

### Phase 17: Deploy + Ops
**Rationale:** Final phase — data must be stable and API tested before production deploy.
**Delivers:** LXC provisioned on PVE02 via provision.sh; PostgreSQL 17 migrated to LXC; Nuxt app deployed pointing to LXC DB; systemd timers configured for weekly ingestion refresh
**Avoids:** PostgreSQL exposure pitfall — bind to 127.0.0.1, use UNIX socket, scram-sha-256 auth; no port 5432 on Proxmox bridge
**Research flag:** Standard ops pattern — well-documented. No phase research needed.

### Phase Ordering Rationale

- **Actors first (phase 10):** Every FK in the schema references actor_id. No other ingestion pipeline can run before this completes. The cross-reference table built in this phase prevents ID corruption in all subsequent phases.
- **Schema before ingestion (phase 9 before 10-14):** Tables must exist before data can be written. One Drizzle migration file per logical change prevents rollback nightmares.
- **Monorepo before schema (phase 8 before 9):** drizzle.config.ts paths, schema import paths, and Python script paths all change in the monorepo restructure — doing this after migrations would require updating migrations again.
- **Ingestion before API (phases 10-14 before 15):** API endpoints without data are untestable and misleading. Build data confidence before exposing endpoints.
- **API before frontend (phase 15 before 16):** Frontend composables bind to specific endpoint shapes. Stable API first means no frontend rework.
- **Questions parallel with CRI (phase 12 || 11):** Questions only depend on actors — the only phases that strictly block each other are 10→11→13 (actor→debates→votes chain).

### Research Flags

Phases needing deeper research during planning:
- **Phase 10 (Actors ingestion):** Tricoteuses source URL migration (Framagit → git.en-root.org) + nossenateurs.fr JSON API format — 1-2 hours sampling
- **Phase 11 (Sénat CRI):** Akoma Ntoso XML format for Senate debates — meaningfully different from DILA CRI format; 2-3 hours research
- **Phase 13 (Senate dumps):** Ameli + Dosleg PostgreSQL 8.4 dump schemas — need to download and inspect before writing ingestion scripts; 1-2 hours
- **Phase 14 (Dossiers):** data.assemblee-nationale.fr dossier format sampling — multiple underdocumented formats; 1-2 hours
- **Phase 15 (API/OpenAPI):** @scalar/nuxt compatibility with current Nuxt 4 — 30 minutes validation
- **Phase 16 (Navette UI):** Custom timeline component design — no existing library covers this; needs component research/prototype

Phases with standard patterns (skip research-phase):
- **Phase 8 (Monorepo):** pnpm workspaces + Turborepo are well-documented; focus on validation checklist
- **Phase 9 (Schema migration):** Drizzle migration docs are authoritative and complete
- **Phase 12 (Questions):** AN open data XML format for questions is documented
- **Phase 17 (Deploy):** Standard LXC + systemd provisioning; existing provision.sh pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All primary sources verified; version compatibility confirmed; existing codebase read directly |
| Features | HIGH | Grounded in competitor analysis of 4+ active sites + 2 official data portals; feature gaps documented with evidence |
| Architecture | HIGH | Existing codebase read directly; monorepo patterns verified against official pnpm + Nuxt docs; Drizzle migration patterns from official docs |
| Pitfalls | HIGH (schema/FTS/migration), MEDIUM (French data specifics), LOW (Sénat cross-referencing) | Schema and FTS pitfalls have official PostgreSQL + Drizzle sources; Senate-specific pitfalls inferred from format documentation + community reports |

**Overall confidence:** HIGH — with 2 known low-confidence areas requiring validation during implementation.

### Gaps to Address

- **Tricoteuses source URL (MEDIUM → needs validation):** git.en-root.org migration from Framagit confirmed via search but not directly fetched (403 on attempt). Validate by cloning during phase 10 planning.
- **Sénat CRI XML structure (LOW):** Akoma Ntoso format confirmed as standard but Senate-specific implementation details unverified. Sample 2-3 recent Senate CR files during phase 11 planning.
- **Senate SQL dump compatibility (LOW):** Ameli + Dosleg use PostgreSQL 8.4-format dumps. Compatibility with PostgreSQL 17's `psql` import unverified. Test during phase 13 planning with a sample dump.
- **@scalar/nuxt Nuxt 4 compatibility (MEDIUM):** Scalar's Nuxt module is newer and integration patterns may differ from older Nuxt 3 examples. Quick validation before phase 15.
- **Drizzle `deputies → actors` rename impact:** The schema rename is flagged as HIGH risk in ARCHITECTURE.md. The exact Drizzle migration SQL for table rename (vs. drop+create) must be validated in a dev DB before touching any staging environment.

## Sources

### Primary (HIGH confidence)
- Existing Poliscope codebase (`server/db/schema.ts`, `server/api/`, `scripts/`) — read directly; architecture decisions grounded in actual code
- [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/) — official AN open data: XML/JSON formats for deputies, votes, amendments, dossiers, questions confirmed
- [data.senat.fr](https://data.senat.fr/donnees/) — official Sénat open data: PostgreSQL dumps for Ameli + Dosleg, XML for CRI confirmed
- [Hono Node.js docs](https://hono.dev/docs/getting-started/nodejs) — @hono/node-server setup, Node 18+ requirement
- [pnpm Workspaces docs](https://pnpm.io/workspaces) — workspace:* protocol, pnpm-workspace.yaml format
- [PostgreSQL GIN index internals](https://pganalyze.com/blog/gin-index) — FTS performance characteristics
- [Drizzle ORM Migrations docs](https://orm.drizzle.team/docs/migrations) — generate + migrate flow, push limitations

### Secondary (MEDIUM confidence)
- [nosdeputes.fr](https://www.nosdeputes.fr/), [datan.fr](https://datan.fr/), [pappers.fr](https://politique.pappers.fr/), [lafabriquedelaloi.fr](https://www.lafabriquedelaloi.fr/) — competitor feature analysis
- [Turborepo vs Nx comparison](https://dev.to/saswatapal/why-i-chose-turborepo-over-nx-monorepo-performance-without-the-complexity-1afp) — community source; recommendation consistent with official docs
- [Nuxt pnpm monorepo path resolution issue](https://github.com/nuxt/nuxt/issues/33826) — confirms Pitfall 1 is real and documented
- [systemd timers vs cron](https://crongen.com/blog/cron-vs-systemd-timers-2026) — Persistent=true behavior, Debian 12 native support
- Drizzle monorepo patterns (GitHub discussion #885) — shared packages/db approach

### Tertiary (LOW confidence)
- Tricoteuses migration from Framagit — new URL git.en-root.org confirmed via search but direct access returned 403; validate during phase 10
- Senate Ameli/Dosleg dump PostgreSQL 8.4 compatibility with PG17 — inferred from format docs; not directly tested
- community.general.proxmox Ansible module instability on Proxmox — reported in community; Terraform instability on Proxmox confirmed separately

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
