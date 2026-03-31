# Poliscope — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Permettre a n'importe qui de chercher et lire ce qu'un parlementaire a dit sur n'importe quel sujet, en quelques clics.
**Current focus:** Phase 13 — API REST Universelle + OpenAPI

## Current Position

- **Milestone** : 2 — Base de Donnees Parlementaire Universelle
- **Phase** : 12 — Ingestion Votes & Scrutins — COMPLETE
- **Plan** : 2/2 — ALL DONE
- **Status** : Phase 12 complete — 7062 scrutins (5908 AN + 1154 Senat) + 1308512 votes in DB, verification PASSED 4/4, next: Phase 13 (API REST)
- **Last activity** : 2026-03-31 — Phase 12 verification PASSED (4/4 must-haves)

Progress: Milestone 1 [███████████████████] 17/17 plans DONE | Milestone 2 [███████████████░] 15/17 plans (partial)

## Accumulated Context

### Key Decisions (Phase 12 — Plan 02)

| Decision | Rationale |
|----------|-----------|
| Text-parse Dosleg SQL dump instead of PG restore | Plain SQL COPY blocks parseable directly — no throwaway DB setup needed |
| official_id = SENAT_{sesann}_{scrnum} | Compound key avoids AN UID collisions; scrutin numbers reset each session |
| Direct actors.official_id match for senators | senmat == official_id exactly (after .strip()) — no cross_references needed unlike AN |
| result = scrpou > scrcon | No explicit result column in scr table — vote counts are definitive |
| votes_abstain = scrvot - scrpou - scrcon | Abstentions not stored directly in scr — computed from voter total |

### Key Decisions (Phase 12 — Plan 01)

| Decision | Rationale |
|----------|-----------|
| syntheseVote.decompte.{pour,contre,abstentions} for AN vote counts | Actual JSON format — research doc incorrectly described syntheseVote.pour.nbrVoix; decompte is the real structure |
| _decode_text() helper in load_actor_cache_an() | psycopg3 binary protocol returns text columns as bytes — must decode; cross_references source_id also had hex-escaped values from Phase 10 original ingestion |
| delegation_actor_id = None for v1 | parDelegation detected (string "true"/"false") but delegation_actor_id tracking deferred — FK requires a second actor lookup not worth implementing now |
| session_id = None | Linking AN scrutins to debate sessions via seanceRef requires lookup not trivial and not needed for Phase 12 |

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

### Key Decisions (Phase 12)

| Decision | Rationale |
|----------|-----------|
| Dosleg text parsing (COPY blocks) instead of pg_restore | PG 8.4 dump incompatible with PG 17 restore — text parsing of COPY blocks is reliable and avoids throwaway DB |
| SENAT_ prefix on scrutin official_id | Prevents collision with AN scrutin UIDs; consistent with SENAT_ prefix on organs from Phase 10 |
| DELETE+INSERT votes per scrutin (not upsert) | Votes have no natural unique key — delete all votes for a scrutin then reinsert is cleaner and idempotent |
| hex-escaped cross_references source_id fixed via SQL UPDATE | psycopg3 binary protocol stored escaped hex instead of text — 577 PA entries corrected in-place |
| syntheseVote.decompte.pour (not syntheseVote.pour.nbrVoix) | Research docs showed wrong path — actual AN JSON uses decompte sub-object for vote counts |

### Key Decisions (Phase 11 — Plan 02)

| Decision | Rationale |
|----------|-----------|
| httpx.stream() + NamedTemporaryFile for cri.zip | 510 MB ZIP — httpx.get().content would OOM on 4GB LXC; streaming to disk avoids full in-memory buffer |
| Name-only senator matching (no href) | Senat CRI XML has no href/ID on Orateur — cross_references not viable; normalize_name() lookup only |
| XVIIE_START = 2022-06-22 | Matches AN XVIIe legislature start for consistent scope across both chambers |
| legislature=17 hardcoded for Senat debates | Senat has no discrete legislature numbering; 17 aligns with concurrent AN XVIIe legislature |

### Key Decisions (Phase 11 — Plan 01)

| Decision | Rationale |
|----------|-----------|
| PA prefix prepend in match_actor() at match time | DILA hrefs give raw numeric IDs (795746); actors.official_id stores PA-prefixed IDs (PA795746) — prepend on lookup, not stored separately |
| chamber='AN' hardcoded in build_debate_record() and build_intervention_records() | Not derived from XML metadata — avoids ambiguity in multi-chamber queries |

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
- **Phase 12** : ~~Schema Dosleg dump PostgreSQL 8.4~~ DONE — Dosleg parsed as text (COPY blocks), no PG restore needed; 1154 scrutins + 361853 votes ingested
- **Phase 13** : Compatibilite @scalar/nuxt avec Nuxt 4 a confirmer (30 min check)
- **Schema** : ~~Rename `deputies -> actors`~~ DONE — migration appliquee avec succes (618 actors, zero perte)

### Pending Todos

None.

## Session Continuity

- **Last session** : 2026-03-31
- **Stopped at** : Phase 12 complete — verification PASSED 4/4
- **Resume** : Phase 13 — API REST Universelle + OpenAPI (votes endpoints, chambre filter, FTS cross-type, Swagger)

## History

- 2026-03-31 : Phase 12 complete — verification PASSED (4/4 must-haves). 7062 scrutins + 1308512 votes bicameraux en base
- 2026-03-31 : Completed 12-02 — Senat scrutins pipeline: 1154 scrutins, 361853 votes, 90.2% match rate via actors.official_id; Dosleg SQL dump text parsing, no PG restore needed
- 2026-03-31 : Completed 12-01 — AN scrutins pipeline: 5908 scrutins, 946659 votes, 574/577 actors linked; fixed psycopg3 bytes decode + hex-escaped cross_references source_id + wrong syntheseVote field path
- 2026-03-30 : Phase 11 complete — 11-04 Task 2 human-verify approved via E2E 9/9: chamber filter tabs, Senat debates navigable, cross-chamber search confirmed
- 2026-03-30 : Completed 11-04 Task 1 — Senat CRI pipeline executed: 413 debates, 292286 interventions, 81.8% match rate, 218535 tagged; fixed 5 bugs in ingest_debates_senat.py (filename regex, XML parser, element structure, mat matching, UnboundLocalError)
- 2026-03-30 : Completed 11-03 — chamber filter on /api/debates (?chamber=AN|Senat), 3-tab selector UI, DebateCard badge, dynamic page title, pagination reset on filter change
- 2026-03-30 : Completed 11-02 — ingest_debates_senat.py (Senat CRI from cri.zip, streaming download, name-only senator matching), run_all.py 9-step pipeline
- 2026-03-30 : Completed 11-01 — ingest_debates.py refactored: actors table (chamber='AN'), PA prefix fix for official_id matching, chamber column on debates+interventions
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
