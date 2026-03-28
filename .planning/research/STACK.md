# Stack Research

**Domain:** Universal Parliamentary Database (BDD Parlementaire Universelle)
**Researched:** 2026-03-28
**Confidence:** HIGH (primary sources verified)
**Scope:** NEW capabilities only — monorepo tooling, multi-source ingestion, API server, API docs, cron scheduling, LXC provisioning

---

## Context: What Already Exists (DO NOT RE-ADD)

| Technology | Version | Status |
|------------|---------|--------|
| Nuxt 4 + Vue 3 + TypeScript | ^4.4.2 | KEEP in packages/web |
| Tailwind CSS v4 + Marbre/Bronze design | ^4.2.2 | KEEP |
| PostgreSQL 17 + Drizzle ORM | 0.45.1 | KEEP, move schema to packages/db |
| Python 3.12 + lxml + httpx | 5.x / 0.27 | KEEP, extend with new scrapers |
| Docker Compose dev environment | — | KEEP |
| Playwright E2E | ^1.58.2 | KEEP |

---

## New Capabilities Required

### 1. Monorepo Tooling

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pnpm workspaces | 9.x (already installed) | Package linking between packages/api, packages/web, packages/db | Already using pnpm; native workspace support with zero extra tooling; `workspace:*` protocol for internal deps |
| Turborepo | ^2.x | Build orchestration, task caching | Lower friction than Nx for a 2-package monorepo; adds parallel builds + caching in <10 min setup; Vercel maintains it |

**Structure:**
```
poliscope/
├── packages/
│   ├── api/          # Hono standalone server
│   ├── web/          # Nuxt 4 (current app/ content moves here)
│   └── db/           # Drizzle schema + migrations (shared)
├── scripts/          # Python ingestion (stays at root — not JS)
├── pnpm-workspace.yaml
├── turbo.json
└── docker-compose.yml
```

**pnpm-workspace.yaml:**
```yaml
packages:
  - 'packages/*'
```

**Why NOT Nx:** Overkill for 2 packages. Nx wants to own your workspace structure and adds significant configuration overhead. Turborepo is additive — drop `turbo.json` in root, done.

### 2. API Server (packages/api)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Hono | ^4.x | HTTP framework for standalone Node.js API | Fastest DX for TypeScript-first REST APIs; Web Standard APIs; 3.5x faster than Express; runs on Node.js 18+ |
| @hono/node-server | ^1.x | Hono adapter for Node.js | Required to run Hono on a Debian LXC (not Cloudflare/Bun) |
| zod | ^3.x | Schema validation + OpenAPI type generation | Already used in frontend ecosystem; bridges validation → OpenAPI spec in one step |

**Why Hono over Fastify:** Poliscope's API is public-read-heavy (parliamentary data). Hono has first-class TypeScript, built-in Zod integration for OpenAPI, and zero boilerplate. Fastify's plugin system adds complexity for a small standalone API package.

**Why NOT Express:** No TypeScript-first design, requires separate OpenAPI tooling, slower than both alternatives.

### 3. API Documentation (OpenAPI/Swagger)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @hono/zod-openapi | ^1.2.x | Route definitions with automatic OpenAPI schema generation | Every API route in packages/api — define once, validates + documents simultaneously |
| @hono/swagger-ui | ^latest | Serve Swagger UI at /docs | Dev + production; allows external devs to explore the API |

**Integration pattern:** Define routes with `createRoute()` → OpenAPI spec auto-generated at `/api/openapi.json` → Swagger UI at `/api/docs`. No separate spec maintenance.

### 4. Cron Scheduling

**Decision: systemd timers on the Debian 12 LXC — NOT a Node.js library.**

Rationale:
- Python ingestion scripts already run as standalone processes (not embedded in Node)
- systemd is the init system on Debian 12 Bookworm — timers are native, logged via journald, support `Persistent=true` (runs missed jobs on boot), and enforce single-instance execution
- node-cron embeds scheduling IN the API process — if the API restarts, scheduled jobs reset
- systemd timers decouple "run API" from "run ingestion" — correct architectural separation

**Implementation:** One `.service` + one `.timer` per data source:
```
/etc/systemd/system/poliscope-ingest-cri.service
/etc/systemd/system/poliscope-ingest-cri.timer
```

**Why NOT node-cron / @nestjs/schedule / Agenda:** All require the Node.js process to stay alive. The ingestion pipeline is Python. Adding a Node.js wrapper around Python scripts is unnecessary indirection.

### 5. Multi-Source Data Ingestion (Python)

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| lxml | ^5.x | XML parsing for CRI, amendements, dossiers | Already in requirements.txt; C-based libxml2 backend; 2-20x faster than xml.etree; supports XPath; handles multi-GB files with `iterparse` |
| httpx | ^0.27 | HTTP client for data.assemblee-nationale.fr / data.senat.fr | Already in use; async-capable; superior to requests for concurrent fetches |
| psycopg[binary] | ^3.1 | PostgreSQL writes | Already in use |

**Data sources and formats:**
- `data.assemblee-nationale.fr` — XML + JSON (deputies, votes, amendments, dossiers, questions)
- `data.senat.fr` — XML (Akoma Ntoso standard), CSV, PostgreSQL dumps
- DILA CRI archives — `.taz` archives with XML (current approach, confirmed working)
- `@tricoteuses/assemblee` — **NOT recommended for ingestion**; it's a JS iterator library wrapping Tricoteuses' cleaned JSON exports from Framagit (now git.en-root.org); too much abstraction for a Python pipeline

**lxml parsing pattern for large files:**
```python
# Stream large XML without loading full tree into memory
for event, elem in etree.iterparse(source, events=("end",), tag="Intervention"):
    process(elem)
    elem.clear()  # critical — prevents memory leak
```

### 6. LXC Provisioning (Proxmox PVE02)

**Decision: Shell script using `pvesh` / `pct` CLI — NOT Ansible.**

Rationale:
- Single server (PVE02), single LXC, one-time provisioning
- Ansible `community.general.proxmox` module works but adds a Python dependency chain and playbook infrastructure for a task that runs once
- `pct create` + `pct exec` shell scripts are 20 lines, readable, reproducible, no external dependencies
- Terraform for Proxmox has known stability issues (confirmed in community reports)

**Provisioning stack:**
```bash
# On PVE02 host:
pct create 200 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname poliscope --memory 2048 --cores 2 --storage local-lvm \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp

pct start 200
pct exec 200 -- bash -c "$(cat provision.sh)"
```

**provision.sh configures:** Node.js 20 LTS (via NodeSource), Python 3.12, PostgreSQL 17 (or remote), pnpm, systemd timers, nginx reverse proxy.

**Why NOT Ansible for this:** Operational overhead outweighs benefit for a single container. Reserve Ansible for when ≥3 containers need identical configuration.

### 7. Shared Database Package (packages/db)

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| drizzle-orm | ^0.45.1 (existing) | Schema definitions shared between packages/api and packages/web | Move `drizzle/` + schema files to `packages/db/`; export all table definitions; both packages import via `workspace:*` |
| drizzle-kit | ^0.31.10 (existing) | Migration generation runs from packages/db | `drizzle.config.ts` lives in packages/db root |

**Pattern:** `packages/db/index.ts` exports all Drizzle table schemas. `packages/api` and `packages/web` (server routes) both import from `@poliscope/db`.

---

## Installation

```bash
# Root monorepo setup
pnpm add -D turbo -w

# packages/api
pnpm add hono @hono/node-server @hono/zod-openapi @hono/swagger-ui zod
pnpm add -D typescript @types/node tsx

# packages/db (extracted from existing drizzle setup)
# Move drizzle-orm + drizzle-kit here, no new packages needed

# Python ingestion (scripts/ — requirements.txt already covers it)
# lxml>=5.0, httpx>=0.27, psycopg[binary]>=3.1 already present
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| pnpm workspaces + Turborepo | Nx | Nx forces workspace restructuring, generators overhead; Turborepo is additive for 2 packages |
| Hono + @hono/zod-openapi | Fastify + fastify-swagger | Fastify has better JSON serialization but more boilerplate; Hono's single-package OpenAPI DX wins for small API |
| systemd timers | node-cron | node-cron embeds scheduling in Node.js process; Python scripts are standalone; systemd is native to Debian 12 |
| pct/pvesh shell scripts | Ansible | Single container, one-time provisioning; Ansible adds YAML playbook infrastructure for zero ongoing benefit |
| lxml iterparse | xml.etree + iterparse | lxml is 2-20x faster, supports XPath for complex CRI structures, already in requirements.txt |
| lxml iterparse | @tricoteuses/assemblee npm package | JS package wrapping cleaned JSON exports — not usable in Python pipeline; adds JS dependency in Python context |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Terraform for Proxmox | Community-reported stability issues; complex state management for a single LXC | `pct` / `pvesh` CLI shell scripts |
| Agenda / Bull / BullMQ | Queue systems for ingestion overkill; adds Redis dependency | systemd timers |
| NestJS for packages/api | Heavy DI framework for a read-heavy REST API; slower cold start | Hono |
| xml.etree (stdlib) | 2-20x slower than lxml on large parliamentary XML; no XPath | lxml (already installed) |
| Turbo/Turborepo remote cache | Requires Vercel account or self-hosted cache server; unnecessary for solo dev | Local cache only (default) |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| hono ^4.x | @hono/node-server ^1.x, @hono/zod-openapi ^1.2.x | All maintained by honojs org, released in sync |
| @hono/zod-openapi ^1.2.x | zod ^3.x | zod v4 not yet supported by zod-openapi as of 2026-03 |
| drizzle-orm ^0.45.x | postgres ^3.x | Existing working combination, keep pinned |
| Node.js 20 LTS | @hono/node-server | Requires Node ≥18.14.1; 20 LTS is on Debian LXC, confirmed compatible |
| lxml ^5.x | Python 3.12 | Compatible; C extension compiles on Debian 12 with `lxml[binary]` or system libxml2 |
| Turborepo ^2.x | pnpm ^9.x | No known issues; Turborepo is runtime-agnostic |

---

## Sources

- [pnpm Workspaces official docs](https://pnpm.io/workspaces) — workspace:* protocol, pnpm-workspace.yaml format (HIGH confidence)
- [Hono Node.js Getting Started](https://hono.dev/docs/getting-started/nodejs) — @hono/node-server setup, Node 18+ requirement (HIGH confidence)
- [Hono Zod OpenAPI docs](https://hono.dev/examples/zod-openapi) — createRoute pattern, /doc endpoint (HIGH confidence)
- [@hono/zod-openapi npm](https://www.npmjs.com/package/@hono/zod-openapi) — version 1.2.3 current (HIGH confidence)
- [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/) — XML + JSON formats confirmed for deputies, votes, amendments (HIGH confidence)
- [data.senat.fr](https://data.senat.fr/) — XML (Akoma Ntoso), CSV, PostgreSQL dump formats (HIGH confidence)
- [lxml performance docs](https://lxml.de/performance.html) — 2-20x faster than xml.etree, iterparse memory pattern (HIGH confidence)
- [Tricoteuses npm package](https://www.npmjs.com/package/@tricoteuses/assemblee) — JS iterator library, not suitable for Python pipeline (MEDIUM confidence — 403 on direct fetch, confirmed via search)
- [systemd timers vs cron](https://crongen.com/blog/cron-vs-systemd-timers-2026) — Debian 12 systemd-native, Persistent=true, journald logging (HIGH confidence)
- [Drizzle monorepo patterns](https://github.com/drizzle-team/drizzle-orm/discussions/885) — shared packages/db approach, workspace exports (MEDIUM confidence)
- [Turborepo vs Nx for small teams](https://dev.to/saswatapal/why-i-chose-turborepo-over-nx-monorepo-performance-without-the-complexity-1afp) — Turborepo additive, Nx prescriptive (MEDIUM confidence — community source)
- community.general.proxmox Ansible module — acknowledged Terraform instability on Proxmox; pct CLI confirmed standard (MEDIUM confidence)

---

*Stack research for: Poliscope BDD Parlementaire Universelle milestone*
*Researched: 2026-03-28*
