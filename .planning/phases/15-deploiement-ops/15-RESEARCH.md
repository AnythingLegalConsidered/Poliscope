# Phase 15: Deploiement & Ops - Research

**Researched:** 2026-04-02
**Domain:** Linux production deployment — Nuxt 3 SSR + PostgreSQL + systemd + nginx
**Confidence:** HIGH

## Summary

The infrastructure baseline (LXC Debian 12 on PVE02, PostgreSQL 17, UFW) was validated in Phase 8. The LXC IP is `192.168.2.200`, hostname `poliscope-db`, vmid 200. Phase 15 builds on this: deploy the Nuxt 3 app onto the same LXC, configure nginx as reverse proxy, manage the Node.js process with PM2 + systemd startup, add a pg_dump daily backup via systemd timer, add a weekly ingestion refresh via systemd timer, and enhance the existing `/api/health` endpoint to include `last_refresh` data.

The key insight for this monorepo is deployment simplicity: build `.output` locally (or on the LXC), copy only the `.output` folder to the LXC, and run `node .output/server/index.mjs` via PM2. The `.output` directory produced by `nuxt build` is fully self-contained — no `node_modules` needed on the server for the web app itself. The Python ingestion stack needs its own `.venv` on the LXC plus the repo code.

The health endpoint `server/api/health.get.ts` already exists with DB connectivity check. It needs a `last_refresh` field (can be a DB table tracking last ingestion timestamp or a file timestamp).

**Primary recommendation:** Deploy as `nuxt build → scp .output → PM2 → nginx → systemd enable`. Use systemd timers (not cron) for both pg_dump and weekly ingestion. Store last_refresh in a DB table updated by ingestion scripts.

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Node.js | 22 LTS (current LTS 2026) | Runtime for Nuxt SSR | LTS support, native ESM |
| PM2 | latest (5.x) | Process manager for Node | Auto-restart, cluster, startup hook |
| nginx | system (debian bookworm) | Reverse proxy, SSL termination | Standard for Node.js apps behind proxy |
| systemd | system | Timer/service for backup + refresh | Already on Debian 12, better than cron |
| pg_dump | PostgreSQL 17 (already installed) | DB backup | Ships with PG17 on LXC |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| nvm or n | latest | Node version management on LXC | Install specific Node LTS on Debian |
| Python 3 + venv | system Python 3 | Ingestion scripts runtime | Already in requirements.txt |
| gzip | system | Compress pg_dump output | `pg_dump ... \| gzip > .sql.gz` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PM2 | pure systemd service | Systemd service is more idiomatic but PM2 is faster to set up and has cluster mode built-in |
| nginx | Caddy | Caddy simpler config but nginx already standard on Debian, no extra repo needed |
| systemd timer | cron | Systemd timers have better logging (journald), dependency management, Persistent=true for missed runs |
| scp .output | git pull + build on server | Build-on-server wastes LXC resources; scp .output is minimal and proven |

**Installation (on LXC):**
```bash
# Node.js via NodeSource (Debian 12)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
# PM2
npm install -g pm2
# nginx
apt-get install -y nginx
```

## Architecture Patterns

### Recommended Deployment Structure (on LXC)
```
/opt/poliscope/
├── .output/              # Built Nuxt app (deployed from local build)
│   └── server/
│       └── index.mjs     # Entry point: node .output/server/index.mjs
├── repo/                 # Full git repo (for ingestion scripts)
│   ├── .env              # Production env (DATABASE_URL, NUXT_SITE_URL)
│   └── packages/
│       └── ingestion/
│           ├── .venv/    # Python venv (created once on LXC)
│           └── scripts/
│               └── run_all.py
├── backups/              # pg_dump output
│   └── poliscope_YYYYMMDD.sql.gz
└── logs/
    └── ingestion.log
```

### Pattern 1: Nuxt 3 Production Build + Deploy

**What:** Build `.output` locally, scp to LXC, PM2 manages the Node process.
**When to use:** VPS/LXC deployments without CI/CD pipeline.

```bash
# LOCAL: build
cd /path/to/poliscope
pnpm --filter web build
# Produces packages/web/.output/

# LOCAL: deploy to LXC
rsync -avz packages/web/.output/ root@192.168.2.200:/opt/poliscope/.output/
# Also copy .env
scp .env root@192.168.2.200:/opt/poliscope/.env

# LXC: start / restart
pm2 restart poliscope || pm2 start /opt/poliscope/.output/server/index.mjs \
  --name poliscope \
  --env production
pm2 save
```

**PM2 ecosystem.config.cjs** (at `/opt/poliscope/ecosystem.config.cjs`):
```js
// Source: https://nuxt.com/docs/getting-started/deployment#nodejs-server
module.exports = {
  apps: [{
    name: 'poliscope',
    script: '/opt/poliscope/.output/server/index.mjs',
    instances: 1,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      PORT: '3000',
      NITRO_PORT: '3000',
    },
    env_file: '/opt/poliscope/.env',
  }],
}
```

> Note: `instances: 'max'` with cluster mode is possible but requires testing — Nuxt 3 SSR is stateless so it's safe, but for a small LXC with 4 vCPU, `instances: 1` is simpler to start.

### Pattern 2: PM2 Systemd Startup

**What:** `pm2 startup systemd` generates a systemd unit that starts PM2 on boot, which in turn starts the Nuxt app.

```bash
# Source: PM2 official docs / https://pm2.keymetrics.io/docs/usage/startup/
pm2 startup systemd
# Execute the output command (sets up systemd unit for current user or root)
pm2 save  # persist current process list
```

### Pattern 3: Nginx Reverse Proxy

**What:** nginx listens on port 80 (and optionally 443 if SSL), forwards to Node on 3000.

```nginx
# /etc/nginx/sites-available/poliscope
server {
    listen 80;
    server_name poliscope.fr _;  # adjust domain

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/poliscope /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
# Also open port 80 in UFW
ufw allow 80/tcp
```

### Pattern 4: pg_dump Systemd Timer (daily backup)

**What:** Two systemd units — a `.service` (oneshot, runs as postgres) and a `.timer` (daily schedule with Persistent=true).

```ini
# /etc/systemd/system/pg-backup-poliscope.service
# Source: https://blog.stefan-koch.name/2024/10/21/backup-postgresql-systemd-timers
[Unit]
Description=Poliscope PostgreSQL daily backup
Requires=postgresql.service
After=postgresql.service

[Service]
Type=oneshot
User=postgres
ExecStart=/opt/poliscope/scripts/pg-backup.sh
StandardOutput=journal
StandardError=journal
```

```ini
# /etc/systemd/system/pg-backup-poliscope.timer
[Unit]
Description=Daily backup timer for Poliscope PostgreSQL

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
#!/bin/bash
# /opt/poliscope/scripts/pg-backup.sh
BACKUP_DIR="/opt/poliscope/backups"
mkdir -p "$BACKUP_DIR"
pg_dump -U poliscope -d poliscope | gzip > "$BACKUP_DIR/poliscope_$(date +%Y%m%d).sql.gz"
# Retain last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

### Pattern 5: Weekly Ingestion Refresh Systemd Timer

**What:** Weekly oneshot service that activates Python venv and runs `run_all.py`. Writes a timestamp to DB on success for the health endpoint.

```ini
# /etc/systemd/system/poliscope-refresh.service
[Unit]
Description=Poliscope weekly data refresh
After=postgresql.service network-online.target

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/poliscope/repo/packages/ingestion/scripts
Environment=PATH=/opt/poliscope/repo/packages/ingestion/.venv/bin:/usr/bin:/bin
ExecStart=/opt/poliscope/repo/packages/ingestion/.venv/bin/python run_all.py
StandardOutput=append:/opt/poliscope/logs/ingestion.log
StandardError=append:/opt/poliscope/logs/ingestion.log
```

```ini
# /etc/systemd/system/poliscope-refresh.timer
[Unit]
Description=Weekly data refresh for Poliscope

[Timer]
OnCalendar=Mon *-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

> The Python venv must be pre-created on the LXC: `cd /opt/poliscope/repo/packages/ingestion && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

### Pattern 6: Health Endpoint Enhancement

The existing `/api/health` endpoint returns `{ status, db, timestamp }`. It needs `last_refresh`.

**Two options:**

**Option A (recommended): DB table `system_metadata`**
```ts
// packages/shared/src/schema.ts — add table
export const systemMetadata = pgTable('system_metadata', {
  key: varchar('key', { length: 64 }).primaryKey(),
  value: text('value').notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
})
```

Ingestion scripts write to this table on completion. Health endpoint reads it:
```ts
// server/api/health.get.ts
const meta = await db.select().from(systemMetadata).where(eq(systemMetadata.key, 'last_refresh'))
return {
  status: 'ok',
  db: 'connected',
  last_refresh: meta[0]?.value ?? null,
  timestamp: new Date().toISOString(),
}
```

**Option B (simpler): timestamp file**
Ingestion script writes `/opt/poliscope/last_refresh.txt`. Health endpoint reads it via `fs.readFileSync`.
Downside: file path is environment-specific, harder to test.

**Recommendation: Option A** — uses the DB (already the source of truth), survives deploys, testable.

### Anti-Patterns to Avoid
- **Running Nuxt as root via PM2**: Use a `poliscope` system user for Node process (root is acceptable for LXC but not ideal).
- **Building on the LXC**: Wastes RAM/CPU during build; `.output` is self-contained, build locally.
- **Storing `.output` in git**: Binary build artifacts don't belong in git — deploy via rsync/scp.
- **Using `pm2 start` without `pm2 save`**: Process list is lost on reboot if not saved.
- **cron for pg_dump**: Systemd timers give journald logging, `Persistent=true` (runs after missed window), and dependency ordering. Use timers.
- **pg_dump as app user instead of postgres**: `pg_dump` works without password prompt when run as the `postgres` Unix user (peer auth). Running as the app user requires password in env.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process management | Custom restart script | PM2 | Auto-restart on crash, cluster mode, memory limits, startup persistence |
| Backup retention | Custom find+rm logic | `find -mtime +30 -delete` in backup script | Trivial but error-prone to get right — use standard find pattern |
| Last-refresh tracking | Parsing log files | DB table `system_metadata` | Atomic, queryable, no file I/O from health endpoint |
| HTTP→HTTPS redirect | Manual nginx redirect blocks | Standard nginx `return 301 https://$host$request_uri` | Trivial nginx pattern, don't overthink |

**Key insight:** The `.output` directory from `nuxt build` is a self-contained Node.js server. No need for `node_modules` on the production server for the web app — this is the biggest deployment simplification in Nuxt 3.

## Common Pitfalls

### Pitfall 1: Nuxt runtimeConfig not loading in production
**What goes wrong:** `NUXT_DATABASE_URL` is set in `.env` on the LXC, but Nuxt ignores it because `nuxt.config.ts` uses `process.env` at build time for some keys, and runtime config needs proper env var prefixing.
**Why it happens:** Nuxt 3 runtimeConfig keys must be overridden via `NUXT_<KEY>` env vars (uppercase, underscores). The `databaseUrl` key → `NUXT_DATABASE_URL`. The `.env` file is NOT automatically loaded in production by Nuxt/Nitro — you must set env vars in the PM2 env or systemd unit.
**How to avoid:** Pass env vars via PM2 `env` block or `env_file`, NOT via `.env` auto-loading. Verify with `pm2 env 0 | grep NUXT_DATABASE_URL`.
**Warning signs:** 503 errors on `/api/health` in production; `databaseUrl` is empty string.

### Pitfall 2: PostgreSQL backup fails silently
**What goes wrong:** `pg_dump` exits 0 but produces an empty file because `postgres` user can't write to the backup dir.
**Why it happens:** Backup dir created by root, not owned by postgres user.
**How to avoid:** `mkdir -p /opt/poliscope/backups && chown postgres:postgres /opt/poliscope/backups`
**Warning signs:** `.sql.gz` files of 0 or ~20 bytes.

### Pitfall 3: Python venv path not activated in systemd unit
**What goes wrong:** `ExecStart=/opt/poliscope/repo/packages/ingestion/.venv/bin/python run_all.py` fails with ModuleNotFoundError.
**Why it happens:** Python finds system packages, not venv packages. The venv python binary should be used directly (no `source activate` in ExecStart — that's a bash builtin).
**How to avoid:** Call the venv Python binary directly: `/path/to/.venv/bin/python script.py`. Don't use `source` in ExecStart.
**Warning signs:** `ModuleNotFoundError: No module named 'psycopg'` in journald.

### Pitfall 4: UFW blocking port 80 for nginx
**What goes wrong:** App deployed but unreachable from outside. Port 80 still blocked.
**Why it happens:** Phase 8 UFW only opened 22, 5432, 3000 from LAN. Port 80 was not opened.
**How to avoid:** `ufw allow 80/tcp` (public) before testing nginx. Check with `ufw status numbered`.
**Warning signs:** `curl http://192.168.2.200` hangs or Connection refused.

### Pitfall 5: PM2 saving stale process list
**What goes wrong:** After a redeploy, PM2 auto-starts the old `.output` path on reboot.
**Why it happens:** `pm2 save` was run before the new deployment path was set.
**How to avoid:** After every deploy, do `pm2 restart poliscope && pm2 save`.
**Warning signs:** App on reboot serves old version.

### Pitfall 6: pnpm workspace symlinks in .output
**What goes wrong:** `packages/web/.output` references `shared` workspace via symlink.
**Why it happens:** When using `shamefully-hoist=true` + pnpm workspaces, the build normally resolves symlinks into the output. But if Nuxt's bundler doesn't fully inline the workspace dep, the output may contain relative symlink references.
**How to avoid:** Verify after `nuxt build` that `.output` works standalone: `node packages/web/.output/server/index.mjs` from the repo root (with env vars set). If it fails, check for workspace symlinks in `.output/server/node_modules/shared`.
**Warning signs:** `Cannot find module 'shared/schema'` when running `.output/server/index.mjs`.

## Code Examples

### Nuxt 3 Production Server Entry Point
```bash
# Source: https://nuxt.com/docs/getting-started/deployment#nodejs-server
# After nuxt build, the standalone server is:
node .output/server/index.mjs
# Env vars override runtime config:
NUXT_DATABASE_URL="postgresql://..." node .output/server/index.mjs
```

### PM2 Ecosystem Config (verified pattern)
```js
// Source: https://nuxt.com/docs/getting-started/deployment#pm2
// ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'poliscope',
    script: '/opt/poliscope/.output/server/index.mjs',
    instances: 1,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      NITRO_PORT: '3000',
    },
  }],
}
```

### Systemd Timer — Enable + Start
```bash
# Source: https://wiki.archlinux.org/title/Systemd/Timers
systemctl daemon-reload
systemctl enable --now pg-backup-poliscope.timer
systemctl enable --now poliscope-refresh.timer
# Verify timers
systemctl list-timers
# Check last run
journalctl -u pg-backup-poliscope.service -n 20
```

### Test OnCalendar expression
```bash
# Verify timer schedule before applying
systemd-analyze calendar "Mon *-*-* 02:00:00"
systemd-analyze calendar "*-*-* 03:00:00"
```

### pg_dump with gzip (Poliscope-specific)
```bash
# Run as postgres user
sudo -u postgres pg_dump -d poliscope | gzip > /opt/poliscope/backups/poliscope_$(date +%Y%m%d).sql.gz
# Restore
gunzip -c poliscope_20260402.sql.gz | psql -U poliscope -d poliscope
```

### Health Endpoint Enhancement
```ts
// packages/web/server/api/health.get.ts
import { sql, eq } from 'drizzle-orm'
import { systemMetadata } from 'shared/schema'

export default defineEventHandler(async () => {
  try {
    await db.execute(sql`SELECT 1`)
    const meta = await db
      .select()
      .from(systemMetadata)
      .where(eq(systemMetadata.key, 'last_refresh'))
      .limit(1)
    return {
      status: 'ok',
      db: 'connected',
      last_refresh: meta[0]?.value ?? null,
      timestamp: new Date().toISOString(),
    }
  } catch (error) {
    throw createError({ statusCode: 503, message: 'Database connection failed' })
  }
})
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `nuxt start` (requires node_modules) | `node .output/server/index.mjs` | Nuxt 3 / Nitro | No node_modules needed on server |
| cron jobs in `/etc/cron.d/` | systemd timers | Debian 12 default | Better logging, Persistent=true, dependency ordering |
| Global node install on server | `.output` self-contained | Nuxt 3 | Only Node runtime needed, not pnpm/packages |
| PM2 cluster with `instances: 'max'` | `instances: 1` or explicit count | — | For a small LXC, cluster overhead not worth it unless CPU-bound |

**Deprecated/outdated:**
- `nuxt start` without `.output`: requires full `node_modules` on server — don't use.
- `pm2 deploy` ecosystem deploy: overkill for a single-server setup — use rsync/scp.

## Open Questions

1. **SSL/HTTPS termination**
   - What we know: NUXT_SITE_URL is `https://poliscope.fr`, suggesting public HTTPS is expected.
   - What's unclear: Whether the LXC is behind a Proxmox reverse proxy (nginx on PVE02?) or needs its own cert. Also unclear if a domain actually points to the LXC IP.
   - Recommendation: Phase 15 scope is LAN-accessible production. Plan for nginx on port 80; mark SSL as out of scope unless domain + cert are confirmed. The UFW currently allows port 3000 from LAN — nginx on 80 is a net improvement.

2. **Ingestion on LXC vs ingestion from dev machine**
   - What we know: `run_all.py` downloads data from public APIs (AN + Sénat) and writes to the DB. It runs from `packages/ingestion/scripts/` with the repo `.env` for `DATABASE_URL`.
   - What's unclear: Does the LXC have outbound internet access? Proxmox LXC containers on a bridge network typically do if the host has routing configured.
   - Recommendation: Assume yes (bridge vmbr0 with gateway at 192.168.2.1 is the standard Proxmox setup), verify during deploy with `curl https://data.assemblee-nationale.fr` from the LXC.

3. **Drizzle migration on first deploy**
   - What we know: Schema has evolved through phases 9-14. The health endpoint references `systemMetadata` table which doesn't exist yet.
   - What's unclear: Whether the current LXC DB schema is up to date with all migrations.
   - Recommendation: Plan 15-01 must include a `pnpm --filter shared db:migrate` step as part of deploy setup.

4. **`last_refresh` update from Python scripts**
   - What we know: `run_all.py` uses psycopg3 directly (not Drizzle). Writing to `system_metadata` requires a direct SQL INSERT/UPDATE.
   - What's unclear: Exact psycopg3 code needed.
   - Recommendation: Add a `write_last_refresh()` function to `db.py` that upserts into `system_metadata` where key='last_refresh'. Call it at end of `run_all.py` on success.

## Sources

### Primary (HIGH confidence)
- https://nuxt.com/docs/getting-started/deployment — Nuxt 3 official deployment docs: Node server, PM2, environment variables
- https://wiki.archlinux.org/title/Systemd/Timers — Systemd timers official reference (ArchWiki = canonical systemd docs)
- Phase 8 VERIFICATION.md (local) — Confirmed: LXC 192.168.2.200, PG17 running, UFW ports 22/5432/3000, Debian 12

### Secondary (MEDIUM confidence)
- https://blog.stefan-koch.name/2024/10/21/backup-postgresql-systemd-timers — pg_dump + systemd service/timer exact config (verified against systemd official syntax)
- https://pm2.keymetrics.io/docs/usage/startup/ — PM2 startup + pm2 save pattern (cross-verified with Nuxt deployment docs)
- https://dev.to/wimadev/deploy-a-nuxt-3-app-on-a-vps-minimal-setup-3h91 — VPS deploy pattern: build locally, scp .output, node index.mjs

### Tertiary (LOW confidence — flag for validation)
- Claim that `.output` from pnpm monorepo build is fully self-contained without workspace symlinks: not directly verified. Test during deploy with standalone run.
- Outbound internet from LXC: assumed from network config but not tested in Phase 8 verification.

## Metadata

**Confidence breakdown:**
- Standard stack (Node, PM2, nginx, pg_dump, systemd): HIGH — official docs + verified infrastructure
- Architecture patterns (deploy flow, timer configs): HIGH — cross-verified from official sources + existing project knowledge
- Pitfalls: MEDIUM to HIGH — runtime config pitfall is HIGH (documented Nuxt behavior), symlink pitfall is MEDIUM (needs validation)
- Health endpoint enhancement: HIGH — existing code seen, pattern is straightforward Drizzle

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable technologies — 30 days)
