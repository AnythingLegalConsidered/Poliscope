# Poliscope — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Permettre a n'importe qui de chercher et lire ce qu'un parlementaire a dit sur n'importe quel sujet, en quelques clics.
**Current focus:** Phase 8 — Monorepo & Infra LXC (Milestone 2 start)

## Current Position

- **Milestone** : 2 — Base de Donnees Parlementaire Universelle
- **Phase** : 8 — Monorepo & Infra LXC
- **Plan** : 1/2 — 08-02 at checkpoint (human-action)
- **Status** : In progress — PAUSED at 08-02 Task 2 (run Ansible playbook)
- **Last activity** : 2026-03-28 — Completed 08-02 Task 1 (Ansible files created), checkpoint at Task 2

Progress: Milestone 1 [███████████████████] 17/17 plans DONE | Milestone 2 [█░░░░░░░░░░░░░░░] 1/16 plans

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

### Key Decisions (Phase 8)

| Decision | Rationale |
|----------|-----------|
| community.proxmox.proxmox (not community.general.proxmox) | community.general.proxmox est deprecie — supprime en community.general 15.0.0 |
| api_password auth par defaut, token en commentaire | Plus simple pour premier run ; token mieux documente pour suite |
| scram-sha-256 dans pg_hba.conf | Default PG17 — ne pas downgrader en md5 |
| UFW default deny + allow explicite 22/5432/3000 LAN | Securite minimale — LXC expose uniquement ce qui est necessaire |

### Blockers / Risks

- **Phase 8 (08-02)** : CHECKPOINT — Ansible playbook pret, attend execution manuelle sur PVE02 (remplir IPs + mot de passe, lancer playbook, verifier psql)
- **Phase 10** : URL Tricoteuses a valider (migration Framagit -> git.en-root.org, retourne 403 en research)
- **Phase 11** : Format XML Senat (Akoma Ntoso) non valide — echantillonner 2-3 CR recents avant implementation
- **Phase 12** : Schema Dosleg dump PostgreSQL 8.4 non inspecte — tester compatibilite avec PG17 avant ingestion
- **Phase 13** : Compatibilite @scalar/nuxt avec Nuxt 4 a confirmer (30 min check)
- **Schema** : Rename `deputies -> actors` est HIGH RISK — toujours tester sur snapshot prod avant migration LXC

### Pending Todos

None.

## Session Continuity

- **Last session** : 2026-03-28
- **Stopped at** : 08-02 Task 2 checkpoint (human-action) — Ansible playbook pret, attend execution
- **Resume** : Apres avoir rempli les variables et execute le playbook → signaler "done" pour continuer

## History

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
