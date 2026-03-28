# Phase 8: Monorepo & Infra LXC - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructurer le repo existant en monorepo pnpm (packages/shared, packages/ingestion, packages/web) et provisionner un LXC Debian 12 sur PVE02 avec PostgreSQL 17 accessible depuis le poste dev. Pas de nouveau code applicatif — infrastructure et organisation uniquement.

</domain>

<decisions>
## Implementation Decisions

### Structure monorepo
- Racine propre : `pnpm-workspace.yaml`, `.env`, `.gitignore`, configs globales
- `packages/shared/` : schema Drizzle, types TS generees, constantes partagees (tags, groupes). Pas d'utils au depart — deplacer dans shared uniquement quand reutilise par web ET ingestion
- `packages/web/` : tout le code Nuxt (app/, server/, components/, composables/, etc.) avec son propre `nuxt.config.ts`, `playwright.config.ts`
- `packages/ingestion/` : scripts Python + venv local (`.venv/` gitignored). pnpm le reference comme workspace pour les scripts npm wrapper
- Configs globaux a la racine, configs specifiques dans leur package (`drizzle.config.ts` dans shared, `playwright.config.ts` dans web)

### Strategie de migration
- Migration incrementale : commits atomiques (1. creer shared + extraire schema, 2. deplacer Nuxt dans web, 3. configurer pnpm workspaces, 4. valider build + E2E)
- Docker Compose supprime — plus de PostgreSQL local, tout pointe vers le LXC
- DB LXC vide en phase 8 — les donnees seront re-ingerees en phase 10 apres le nouveau schema (phase 9)
- Build Nuxt ET tests E2E (11 tests Playwright) doivent passer apres restructuration

### Config LXC & reseau
- LXC Debian 12 sur PVE02 — 4 vCPU, 4 Go RAM, 100 Go disk
- IP fixe sur le LAN (bridge vmbr0 de PVE02), pas de VLAN
- Acces SSH via cle existante de Ianis (copiee par le playbook)
- PostgreSQL 17 ecoute sur l'IP du LXC, accessible depuis le subnet LAN (`pg_hba.conf` + `listen_addresses = '*'`)
- Firewall PVE limite aux ports 22 (SSH), 5432 (PG), 3000 (Nuxt)
- Provisionnement via playbook Ansible idempotent (PG17, user/db poliscope, pg_hba, firewall, cle SSH)

### Workflow dev local
- `pnpm dev` = `pnpm --filter web dev` = `nuxt dev`. Pas de watcher sur shared (types resolus directement par TS)
- `.env.example` avec placeholders + `.env` reel gitignored pointant vers l'IP du LXC
- Migrations Drizzle depuis `packages/shared` : `pnpm --filter shared db:migrate`
- Ingestion via `pnpm run ingest` a la racine (wrapper vers Python dans packages/ingestion)

### Claude's Discretion
- Contenu exact de packages/shared au-dela du schema (evaluer le code existant)
- Organisation interne de packages/ingestion (structure dossiers Python)
- Ordre exact des commits de migration
- Configuration Ansible detaillee (roles, variables)
- Besoin ou non de turbo.json pour orchestrer les builds

</decisions>

<specifics>
## Specific Ideas

- Docker Compose est supprime des phase 8 — le LXC est la seule DB, meme en dev
- Le playbook Ansible doit etre idempotent (reexecutable sans casser l'etat)
- Les scripts Python existants doivent s'executer depuis packages/ingestion sans changer leurs imports (success criteria roadmap)
- La DB est vide en phase 8 — pas de migration de donnees, juste PG17 up et accessible

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-monorepo-infra-lxc*
*Context gathered: 2026-03-28*
