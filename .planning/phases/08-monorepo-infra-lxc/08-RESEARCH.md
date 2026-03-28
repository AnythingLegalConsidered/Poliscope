# Phase 8: Monorepo & Infra LXC - Research

**Researched:** 2026-03-28
**Domain:** pnpm workspaces monorepo + Ansible/Proxmox LXC provisioning + PostgreSQL 17
**Confidence:** HIGH (pnpm workspaces), MEDIUM (Ansible/Proxmox), HIGH (PostgreSQL 17 install)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Structure monorepo
- Racine propre : `pnpm-workspace.yaml`, `.env`, `.gitignore`, configs globales
- `packages/shared/` : schema Drizzle, types TS generees, constantes partagees (tags, groupes). Pas d'utils au depart — deplacer dans shared uniquement quand reutilise par web ET ingestion
- `packages/web/` : tout le code Nuxt (app/, server/, components/, composables/, etc.) avec son propre `nuxt.config.ts`, `playwright.config.ts`
- `packages/ingestion/` : scripts Python + venv local (`.venv/` gitignored). pnpm le reference comme workspace pour les scripts npm wrapper
- Configs globaux a la racine, configs specifiques dans leur package (`drizzle.config.ts` dans shared, `playwright.config.ts` dans web)

#### Strategie de migration
- Migration incrementale : commits atomiques (1. creer shared + extraire schema, 2. deplacer Nuxt dans web, 3. configurer pnpm workspaces, 4. valider build + E2E)
- Docker Compose supprime — plus de PostgreSQL local, tout pointe vers le LXC
- DB LXC vide en phase 8 — les donnees seront re-ingerees en phase 10 apres le nouveau schema (phase 9)
- Build Nuxt ET tests E2E (11 tests Playwright) doivent passer apres restructuration

#### Config LXC & reseau
- LXC Debian 12 sur PVE02 — 4 vCPU, 4 Go RAM, 100 Go disk
- IP fixe sur le LAN (bridge vmbr0 de PVE02), pas de VLAN
- Acces SSH via cle existante de Ianis (copiee par le playbook)
- PostgreSQL 17 ecoute sur l'IP du LXC, accessible depuis le subnet LAN (`pg_hba.conf` + `listen_addresses = '*'`)
- Firewall PVE limite aux ports 22 (SSH), 5432 (PG), 3000 (Nuxt)
- Provisionnement via playbook Ansible idempotent (PG17, user/db poliscope, pg_hba, firewall, cle SSH)

#### Workflow dev local
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

This phase has two parallel workstreams: (1) restructure the existing flat Nuxt repo into a pnpm monorepo with three packages, and (2) provision a Debian 12 LXC on PVE02 with PostgreSQL 17 via Ansible.

The existing repo is a standard Nuxt 4 app with: `server/db/schema.ts` (Drizzle schema), `server/utils/db.ts` (DB client), Python scripts in `scripts/` with relative imports from each other, and 11 Playwright E2E tests. The shared `types/index.ts` is currently empty (`export {}`). The current `drizzle.config.ts` at root points to `./server/db/schema.ts`. The Python scripts use bare module imports (`from config import ...`, `from db import ...`) which rely on running from the `scripts/` directory — this constraint must be preserved in `packages/ingestion/`.

The Ansible side is straightforward: community.proxmox collection (replacing deprecated community.general.proxmox), PostgreSQL 17 from PGDG repo, community.postgresql collection for DB/user creation, nftables or ufw for port filtering. No Turbo needed — pnpm filter commands are sufficient for this three-package repo.

**Primary recommendation:** Use pnpm workspaces with `packages/*` glob, `.npmrc` with `shamefully-hoist=true` for Nuxt compatibility, `workspace:*` protocol for cross-package deps, and a single Ansible playbook split into two plays (LXC creation on PVE02 host, then PG config on LXC).

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| pnpm workspaces | pnpm 9+ (current) | Monorepo orchestration | Built-in, no extra tooling |
| `pnpm-workspace.yaml` | — | Declare workspace packages | Required root file for pnpm monorepo |
| `workspace:*` protocol | pnpm native | Cross-package deps | Refuses to resolve outside workspace |
| community.proxmox collection | latest | Create LXC via Ansible | New canonical module (community.general deprecated) |
| community.postgresql collection | latest | Manage PG users/dbs/hba | Ansible-native PG management |
| PostgreSQL 17 PGDG | 17.x | Database | Debian 12 default repo only ships PG 15 |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `.npmrc` shamefully-hoist | — | Nuxt dependency resolution | Required for Nuxt in pnpm monorepo |
| `ansible.posix.firewalld` | — | Firewall rules in LXC | If firewalld installed; alternative: ufw module |
| `python3-psycopg2` | apt | Ansible PostgreSQL module dep | Required on Ansible controller for community.postgresql |
| `dotenv-cli` | npm | Load root `.env` in sub-packages | If scripts in packages need env vars at dev time |

### No Turbo Needed
For a 3-package monorepo without complex build graphs, `pnpm --filter` is sufficient. Turbo adds value when you have many packages with inter-dependencies and want parallel build caching. Skip it.

### Installation
```bash
# At repo root
pnpm install  # installs all workspace packages

# Install Ansible collections on controller
ansible-galaxy collection install community.proxmox community.postgresql ansible.posix
```

## Architecture Patterns

### Recommended Project Structure
```
poliscope/                      # repo root
├── pnpm-workspace.yaml         # declares packages/*
├── .npmrc                      # shamefully-hoist=true
├── .env                        # gitignored, real values
├── .env.example                # committed, placeholders
├── .gitignore                  # root-level
├── package.json                # root scripts (dev, ingest, etc.)
├── packages/
│   ├── shared/
│   │   ├── package.json        # name: "shared", private: true
│   │   ├── drizzle.config.ts   # points to ./src/schema.ts, out: ./drizzle
│   │   ├── drizzle/            # migration SQL files
│   │   └── src/
│   │       ├── schema.ts       # moved from server/db/schema.ts
│   │       ├── types.ts        # moved from shared/types/index.ts (empty now)
│   │       └── index.ts        # re-exports schema + types
│   ├── web/
│   │   ├── package.json        # name: "web", deps include "shared": "workspace:*"
│   │   ├── nuxt.config.ts      # unchanged content
│   │   ├── playwright.config.ts # rootDir updated to new location
│   │   ├── tsconfig.json       # Nuxt-generated, unchanged
│   │   ├── app/
│   │   ├── server/
│   │   │   ├── api/
│   │   │   ├── utils/
│   │   │   └── db/             # schema.ts replaced by import from shared
│   │   ├── e2e/
│   │   └── public/
│   └── ingestion/
│       ├── package.json        # name: "ingestion", private: true, scripts.ingest
│       ├── requirements.txt    # moved from scripts/
│       ├── .venv/              # gitignored
│       └── scripts/            # Python files, unchanged relative imports
│           ├── config.py       # loads ../.env (needs path update)
│           ├── db.py
│           ├── run_all.py
│           └── ...
├── ansible/
│   ├── inventory.ini           # PVE02 + poliscope-lxc hosts
│   ├── playbook.yml            # 2 plays: create LXC + configure PG
│   └── group_vars/
│       └── all.yml             # variables (vmid, ip, credentials)
└── drizzle/                    # can be removed (moved to packages/shared/drizzle/)
```

### Pattern 1: pnpm-workspace.yaml
**What:** Root file declaring which directories are workspace packages.
**When to use:** Required for all pnpm monorepos.

```yaml
# Source: https://pnpm.io/pnpm-workspace_yaml
packages:
  - 'packages/*'
```

### Pattern 2: workspace: Protocol for Cross-Package Deps
**What:** Declares that a dep must come from the local workspace.

```json
// packages/web/package.json
{
  "name": "web",
  "private": true,
  "dependencies": {
    "shared": "workspace:*"
  }
}
```

pnpm refuses to resolve `workspace:*` to any registry package — protects against accidental external resolution.

### Pattern 3: Root package.json Scripts
**What:** Delegate commands to workspace packages via `--filter`.

```json
// Root package.json
{
  "name": "poliscope",
  "private": true,
  "scripts": {
    "dev": "pnpm --filter web dev",
    "build": "pnpm --filter web build",
    "test:e2e": "pnpm --filter web test:e2e",
    "db:migrate": "pnpm --filter shared db:migrate",
    "ingest": "pnpm --filter ingestion ingest"
  }
}
```

### Pattern 4: Python Package as pnpm Workspace Member
**What:** `packages/ingestion` has a minimal `package.json` that only wraps Python CLI calls.
**Key insight:** pnpm does not manage Python — it just provides a consistent script entry point.

```json
// packages/ingestion/package.json
{
  "name": "ingestion",
  "private": true,
  "scripts": {
    "ingest": "cd scripts && python run_all.py",
    "ingest:limit": "cd scripts && python run_all.py --limit"
  }
}
```

The Python scripts use bare imports (`from config import DATABASE_URL`) that work because they are run from the `scripts/` directory. The `cd scripts &&` wrapper preserves this.

**Critical: `config.py` path fix.** Currently `config.py` loads `.env` relative to `scripts/` directory, one level up (`../`). After moving `scripts/` to `packages/ingestion/scripts/`, the `.env` is now **3 levels up** (`../../..`). Update config.py:

```python
# packages/ingestion/scripts/config.py - path must reach repo root
_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
```

### Pattern 5: Playwright rootDir in packages/web
**What:** After moving Nuxt to `packages/web/`, the playwright config's `rootDir` must point to the correct directory.

```typescript
// packages/web/playwright.config.ts
use: {
  nuxt: {
    rootDir: fileURLToPath(new URL('.', import.meta.url)),
    // '.', import.meta.url points to packages/web/ — correct
  },
}
```

`import.meta.url` resolves relative to the config file itself. Since the config is now in `packages/web/`, `new URL('.', import.meta.url)` already points to the right place — **no change needed to the rootDir expression**, only the file location changes.

The `NUXT_DATABASE_URL` fallback default in playwright.config.ts should be updated to point to the LXC IP:
```typescript
process.env.NUXT_DATABASE_URL ??= 'postgresql://poliscope:poliscope_dev@<LXC_IP>:5432/poliscope'
```

### Pattern 6: drizzle.config.ts in packages/shared
**What:** Drizzle config moves to `packages/shared/` and references schema relative to its own location.

```typescript
// packages/shared/drizzle.config.ts
import 'dotenv/config'
import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  dialect: 'postgresql',
  schema: './src/schema.ts',
  out: './drizzle',
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
})
```

Note: `DATABASE_URL` (not `NUXT_DATABASE_URL`) for Drizzle Kit — it runs outside Nuxt. The root `.env` must define both `DATABASE_URL` and `NUXT_DATABASE_URL`.

### Pattern 7: Ansible Two-Play Playbook
**What:** Play 1 runs on the PVE02 host to create the LXC. Play 2 runs on the new LXC to install/configure PostgreSQL.

```yaml
# ansible/playbook.yml
---
- name: Create poliscope LXC on PVE02
  hosts: pve02
  gather_facts: false
  tasks:
    - name: Create LXC container
      community.proxmox.proxmox:
        vmid: "{{ lxc_vmid }}"
        node: pve02
        api_host: "{{ pve_host }}"
        api_user: "{{ pve_api_user }}"
        api_token_id: "{{ pve_api_token_id }}"
        api_token_secret: "{{ pve_api_token_secret }}"
        hostname: poliscope-db
        ostemplate: "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
        cores: 4
        memory: 4096
        disk: "local-lvm:100"
        netif: '{"net0":"name=eth0,bridge=vmbr0,ip={{ lxc_ip }}/24,gw={{ lxc_gw }}"}'
        pubkey: "{{ lookup('file', '~/.ssh/id_ed25519.pub') }}"
        onboot: true
        state: present

- name: Configure PostgreSQL 17 on LXC
  hosts: poliscope_lxc
  become: true
  tasks:
    # Install PG17 from PGDG
    - name: Install prerequisites
      apt:
        name: [curl, ca-certificates, gnupg, python3-psycopg2]
        update_cache: true

    - name: Add PGDG signing key
      apt_key:
        url: https://www.postgresql.org/media/keys/ACCC4CF8.asc
        keyring: /usr/share/keyrings/postgresql-archive-keyring.gpg
        state: present

    - name: Add PGDG repository
      apt_repository:
        repo: "deb [signed-by=/usr/share/keyrings/postgresql-archive-keyring.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main"
        filename: pgdg

    - name: Install PostgreSQL 17
      apt:
        name: [postgresql-17, postgresql-client-17]
        update_cache: true

    - name: Ensure PostgreSQL is running
      service:
        name: postgresql
        state: started
        enabled: true

    # Configure remote access
    - name: Set listen_addresses to *
      lineinfile:
        path: /etc/postgresql/17/main/postgresql.conf
        regexp: "^#?listen_addresses"
        line: "listen_addresses = '*'"
      notify: restart postgresql

    - name: Allow LAN subnet in pg_hba.conf
      community.postgresql.postgresql_pg_hba:
        dest: /etc/postgresql/17/main/pg_hba.conf
        contype: host
        databases: poliscope
        users: poliscope
        source: "{{ lan_subnet }}"
        method: scram-sha-256
      notify: restart postgresql

    # Create DB and user
    - name: Create poliscope database
      community.postgresql.postgresql_db:
        name: poliscope
        state: present
      become_user: postgres

    - name: Create poliscope user
      community.postgresql.postgresql_user:
        name: poliscope
        password: "{{ pg_password }}"
        db: poliscope
        priv: ALL
        state: present
      become_user: postgres

    # Firewall
    - name: Allow SSH
      community.general.ufw:
        rule: allow
        port: '22'
        proto: tcp

    - name: Allow PG from LAN only
      community.general.ufw:
        rule: allow
        port: '5432'
        src: "{{ lan_subnet }}"
        proto: tcp

    - name: Allow Nuxt port from LAN
      community.general.ufw:
        rule: allow
        port: '3000'
        src: "{{ lan_subnet }}"
        proto: tcp

    - name: Enable ufw
      community.general.ufw:
        state: enabled
        default: deny

  handlers:
    - name: restart postgresql
      service:
        name: postgresql
        state: restarted
```

### Anti-Patterns to Avoid
- **Installing Nuxt dependencies at workspace root:** Each package manages its own deps. Root `package.json` has no `dependencies`, only `devDependencies` for tooling shared across all packages (e.g., TypeScript if used globally).
- **Putting drizzle.config.ts at repo root:** It belongs in `packages/shared/` where the schema lives.
- **Using `npm run` instead of `pnpm run` in root scripts:** Always use `pnpm --filter` to target workspace packages.
- **Not setting `shamefully-hoist=true`:** Nuxt has peer dependency resolution issues in strict pnpm mode — hoisting is the established fix as of 2025.
- **Running Ansible PostgreSQL modules without `python3-psycopg2`:** The `community.postgresql` collection requires the psycopg2 Python library on the managed node.
- **Using `community.general.proxmox` module:** Deprecated, migrating to `community.proxmox.proxmox`. Use `community.proxmox` collection from start.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LXC creation | Manual `pct create` commands | `community.proxmox.proxmox` Ansible module | Idempotency, state management, API-driven |
| PG user/db/hba creation | Raw SQL in shell tasks | `community.postgresql.*` modules | Handles idempotency, password hashing, pg_hba format |
| Cross-package dep linking | Symlinks or `npm link` | `workspace:*` protocol | pnpm manages symlinks in node_modules automatically |
| Build orchestration | Custom Makefile | `pnpm --filter` commands | Native, no extra tooling |
| Firewall rules | Raw `iptables` or `nft` commands | `community.general.ufw` module | Idempotent, declarative, readable |

**Key insight:** The entire Ansible/Proxmox/PostgreSQL stack has mature Ansible modules. Never use shell tasks for operations that have dedicated modules — modules are idempotent, shell tasks are not.

## Common Pitfalls

### Pitfall 1: Python Bare Imports Break After Move
**What goes wrong:** Python scripts use `from config import ...` and `from db import ...` with no package prefix. These work only when Python's cwd or sys.path includes the `scripts/` directory.
**Why it happens:** The scripts were written to be run as `cd scripts && python run_all.py`. After moving to `packages/ingestion/scripts/`, if the npm wrapper script doesn't `cd` into the right directory, imports fail.
**How to avoid:** The `package.json` script wrapper must `cd scripts && python run_all.py`. Confirm with `python -c "import config"` from `packages/ingestion/scripts/`.
**Warning signs:** `ModuleNotFoundError: No module named 'config'` when running `pnpm run ingest`.

### Pitfall 2: config.py .env Path is Wrong After Move
**What goes wrong:** `config.py` currently does `os.path.join(__file__, '..', '.env')` (one level up from `scripts/` = project root). After move to `packages/ingestion/scripts/`, one level up is `packages/ingestion/`, not repo root.
**Why it happens:** Hardcoded relative path that assumed `scripts/` was at repo root.
**How to avoid:** Update to `os.path.join(__file__, '..', '..', '..', '.env')` (3 levels up to repo root).
**Warning signs:** `KeyError: 'DATABASE_URL'` when running any Python script.

### Pitfall 3: Nuxt Fails to Find server/ or app/ in Monorepo
**What goes wrong:** Nuxt looks for `server/`, `app/`, `pages/` relative to `rootDir`. If `nuxt.config.ts` is invoked from repo root instead of `packages/web/`, all paths break.
**Why it happens:** Running `nuxt dev` from wrong directory, or a misconfigured `rootDir` in Playwright config.
**How to avoid:** Always run Nuxt commands via `pnpm --filter web dev` (not from root directly). Playwright `rootDir` must use `fileURLToPath(new URL('.', import.meta.url))` which is relative to the config file — if the config is in `packages/web/`, this is already correct.
**Warning signs:** `ENOENT: no such file or directory, scandir 'packages/web/server'` during Nuxt startup.

### Pitfall 4: drizzle.config.ts Schema Path Broken
**What goes wrong:** If `drizzle.config.ts` still references `./server/db/schema.ts`, it fails because schema moved to `packages/shared/src/schema.ts`.
**Why it happens:** Copying config without updating relative paths.
**How to avoid:** After moving schema to `packages/shared/src/schema.ts`, the config at `packages/shared/drizzle.config.ts` must reference `./src/schema.ts`.
**Warning signs:** `Cannot find module './server/db/schema'` when running `pnpm --filter shared db:generate`.

### Pitfall 5: PostgreSQL 17 Not Available from Default Debian 12 Repos
**What goes wrong:** `apt install postgresql` on Debian 12 installs PostgreSQL 15, not 17.
**Why it happens:** Debian 12 (Bookworm) ships PG 15 in its default repos. PG 17 requires the PGDG external repository.
**How to avoid:** Always add PGDG repo before installing. Ansible task order: add key → add repo → apt update → install postgresql-17.
**Warning signs:** `postgresql --version` returns 15.x after install.

### Pitfall 6: LXC Template Not Downloaded on PVE02
**What goes wrong:** Ansible LXC creation fails with "template not found" because the Debian 12 template tarball isn't in PVE02's local storage.
**Why it happens:** PVE templates must be downloaded separately before they can be used as `ostemplate`.
**How to avoid:** Either download manually via PVE UI first, or add an Ansible task using `proxmox_template` or shell to `pveam download local debian-12-standard`.
**Warning signs:** `ostemplate 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst' does not exist`.

### Pitfall 7: E2E Tests Fail Because DB is Empty
**What goes wrong:** Playwright E2E tests load real pages that show debate cards. The tests expect data (e.g., `expect(cards.first()).toBeVisible()`). With an empty LXC DB, those tests fail.
**Why it happens:** The current tests assume a populated database. Phase 8 DB is intentionally empty.
**How to avoid:** For phase 8 validation, E2E tests must be run against a DB with at least minimal seed data, OR the success criterion must be limited to "build passes + Nuxt server starts" rather than full E2E. Check if a DB seed script exists or create one with 1-2 debates + deputies.
**Warning signs:** `expect(cards.first()).toBeVisible()` timeout in E2E.

### Pitfall 8: community.general.proxmox vs community.proxmox.proxmox
**What goes wrong:** Documentation and examples mix two module names. `community.general.proxmox` is deprecated and will be removed in community.general 15.0.0.
**Why it happens:** The module was recently split out to a dedicated `community.proxmox` collection.
**How to avoid:** Install `community.proxmox` collection and use `community.proxmox.proxmox` in all tasks. Do not mix.
**Warning signs:** Deprecation warnings during playbook run: `[DEPRECATION WARNING]: community.general.proxmox is deprecated`.

## Code Examples

### pnpm-workspace.yaml (exact)
```yaml
# Source: https://pnpm.io/pnpm-workspace_yaml
packages:
  - 'packages/*'
```

### .npmrc (exact)
```
# Required for Nuxt peer dependency resolution in pnpm monorepo
shamefully-hoist=true
```

### packages/shared/package.json
```json
{
  "name": "shared",
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:push": "drizzle-kit push",
    "db:studio": "drizzle-kit studio"
  },
  "dependencies": {
    "drizzle-orm": "workspace:*"
  },
  "devDependencies": {
    "drizzle-kit": "workspace:*"
  }
}
```

Note: using `workspace:*` to reuse the already-installed drizzle-orm from web package (pnpm deduplicates). Alternatively pin the same version.

### packages/ingestion/package.json
```json
{
  "name": "ingestion",
  "private": true,
  "scripts": {
    "ingest": "cd scripts && python run_all.py",
    "ingest:limit": "cd scripts && python run_all.py --limit",
    "venv:create": "python -m venv .venv",
    "venv:install": ".venv/bin/pip install -r requirements.txt"
  }
}
```

### Root package.json scripts section
```json
{
  "name": "poliscope",
  "private": true,
  "scripts": {
    "dev": "pnpm --filter web dev",
    "build": "pnpm --filter web build",
    "preview": "pnpm --filter web preview",
    "test:e2e": "pnpm --filter web test:e2e",
    "db:migrate": "pnpm --filter shared db:migrate",
    "db:generate": "pnpm --filter shared db:generate",
    "db:studio": "pnpm --filter shared db:studio",
    "ingest": "pnpm --filter ingestion ingest"
  }
}
```

### packages/web/server/utils/db.ts (after migration)
```typescript
// Import schema from shared package instead of local path
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from 'shared/src/schema'  // via workspace: resolution

const client = postgres(useRuntimeConfig().databaseUrl)
export const db = drizzle(client, { schema })
```

Note: The import path `'shared/src/schema'` works because `shared` is declared as a workspace dep in `packages/web/package.json` and pnpm creates a symlink. Alternatively use `'#shared'` with a package.json `imports` field.

### PGDG PostgreSQL 17 install sequence (verified)
```bash
# Source: https://computingforgeeks.com/install-postgresql-debian/
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  gpg --dearmor -o /usr/share/keyrings/postgresql-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/postgresql-archive-keyring.gpg] \
  http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list

apt update && apt install -y postgresql-17 postgresql-client-17
systemctl enable --now postgresql
```

### pg_hba.conf entry for LAN access (scram-sha-256)
```
# TYPE  DATABASE   USER        ADDRESS          METHOD
host    poliscope  poliscope   192.168.1.0/24   scram-sha-256
```

PG 17 defaults to `scram-sha-256`. Do not downgrade to `md5`.

### .env.example (root)
```bash
# Database — point to LXC IP
DATABASE_URL=postgresql://poliscope:<password>@<LXC_IP>:5432/poliscope
NUXT_DATABASE_URL=postgresql://poliscope:<password>@<LXC_IP>:5432/poliscope

# Site
NUXT_SITE_URL=https://poliscope.fr
```

`DATABASE_URL` is used by Drizzle Kit (`packages/shared/drizzle.config.ts`).
`NUXT_DATABASE_URL` is used by Nuxt runtimeConfig (`nuxt.config.ts`).
Both must be set in `.env`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `community.general.proxmox` | `community.proxmox.proxmox` | 2024, collection split | Must install `community.proxmox` collection |
| Yarn/npm workspaces | pnpm workspaces | 2022–2023 | Faster, disk efficient, stricter isolation |
| Docker Compose local PG | Remote LXC PG | Phase 8 | `docker-compose.yml` deleted entirely |
| Flat repo `scripts/` | `packages/ingestion/scripts/` | Phase 8 | Python path adjustments required |

**Deprecated/outdated:**
- `docker-compose.yml`: Remove entirely in phase 8
- `package-lock.json`: Already has `pnpm-lock.yaml` — delete `package-lock.json`
- `shared/types/index.ts`: Empty file, superseded by `packages/shared/src/types.ts`

## Open Questions

1. **Debian 12 template availability on PVE02**
   - What we know: Ansible will need the template tarball to exist locally on PVE02
   - What's unclear: Whether `debian-12-standard_12.7-1_amd64.tar.zst` is already downloaded on PVE02
   - Recommendation: Add a `pveam download local debian-12-standard_12.7-1_amd64.tar.zst` task before LXC creation, with `creates:` idempotency guard

2. **PVE02 API access method (API token vs password)**
   - What we know: `community.proxmox.proxmox` supports both `api_password` and `api_token_id + api_token_secret`
   - What's unclear: Which auth method is configured on PVE02
   - Recommendation: Use API token (more secure, no password in vars). Create a `ansible-automation@pve` user with limited Sys.Modify + VM.Allocate privileges.

3. **LAN subnet for pg_hba.conf**
   - What we know: PVE02 is on home LAN, vmbr0 bridge. LXC gets IP on same subnet.
   - What's unclear: Exact subnet (192.168.x.0/24 vs 10.x.0/24)
   - Recommendation: Use a variable `{{ lan_subnet }}` in playbook — fill in `group_vars/all.yml` before running.

4. **E2E tests against empty DB in phase 8**
   - What we know: 3 of 4 E2E test suites (home, debate, deputies, search) require actual data to pass
   - What's unclear: Whether phase 8 success criterion includes passing E2E or just "Nuxt builds and server starts"
   - Recommendation: Create a minimal seed SQL file in `packages/shared/drizzle/seed.sql` with 2-3 rows per table. Run seed after `db:migrate` for test validation. This is a small addition but avoids blocking the validation step.

## Sources

### Primary (HIGH confidence)
- https://pnpm.io/workspaces — pnpm workspace protocol, workspace: syntax, filter commands
- https://pnpm.io/pnpm-workspace_yaml — exact pnpm-workspace.yaml format
- https://orm.drizzle.team/docs/drizzle-config-file — drizzle.config.ts format, monorepo guidance
- https://github.com/nuxt/test-utils — playwright.config.ts rootDir pattern (import.meta.url)
- https://computingforgeeks.com/install-postgresql-debian/ — PG17 on Debian 12, PGDG repo commands (tested March 2026)

### Secondary (MEDIUM confidence)
- https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/ — community.proxmox module (module existed, docs were Cloudflare-blocked but module name confirmed by multiple sources)
- https://github.com/geerlingguy/ansible-role-postgresql — established PG role, confirms community.postgresql collection usage
- Multiple WebSearch results confirming `community.general.proxmox` deprecation in favor of `community.proxmox.proxmox`

### Tertiary (LOW confidence — validate before use)
- The exact `disk_volume` parameter syntax for `community.proxmox.proxmox` — the older `disk` string format (`"local-lvm:100"`) is shown in examples but the newer `disk_volume` parameter added in community.general 9.2.0 may have different syntax
- Exact Ansible `netif` JSON format for static IP assignment — verify against current docs before running playbook

## Metadata

**Confidence breakdown:**
- Standard stack (pnpm workspaces): HIGH — verified against official pnpm docs
- Nuxt in monorepo (.npmrc, rootDir): HIGH — multiple sources, verified pattern
- Python path adjustments: HIGH — direct code inspection, deterministic
- Architecture patterns: HIGH — derived from codebase inspection + verified docs
- Ansible/Proxmox LXC creation: MEDIUM — module confirmed, exact parameter syntax needs validation
- PG17 installation: HIGH — verified commands from tested guide (March 2026)
- Pitfalls: HIGH — derived from direct codebase inspection (actual paths, actual imports)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (pnpm/Nuxt stable); 2026-04-07 for Ansible module parameters (fast-moving)
