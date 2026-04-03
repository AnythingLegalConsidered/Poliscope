---
phase: 15-deploiement-ops
plan: "01"
subsystem: infra
tags: [nginx, pm2, node22, systemd, scp, deploy, lxc]
status: complete

requires:
  - phase: 08-infrastructure
    provides: LXC 192.168.2.200 with PG17, UFW, Debian 12

provides:
  - deploy/provision.sh — one-time LXC setup (Node 22, PM2, nginx, dirs, UFW)
  - deploy/deploy.sh — repeatable local build + scp/rsync + PM2 restart
  - deploy/ecosystem.config.cjs — PM2 process config with --env-file for .env loading
  - deploy/nginx/poliscope.conf — nginx reverse proxy to localhost:3000
  - deploy/.env.production.example — template with NUXT_DATABASE_URL placeholder

affects: [phase-15-plan-02]

tech-stack:
  added: [PM2 6.0.14, Node.js 22.22.2, nginx 1.22.1]
  patterns:
    - Build .output locally, scp to LXC — no node_modules on server
    - PM2 + systemd startup hook for Node process management
    - nginx reverse proxy on port 80 → Node on port 3000
    - Node 22 --env-file for environment variable loading

key-files:
  created:
    - deploy/provision.sh
    - deploy/deploy.sh
    - deploy/ecosystem.config.cjs
    - deploy/nginx/poliscope.conf
    - deploy/.env.production.example
  modified:
    - .gitignore (deploy/.env.production excluded, .env.production.example allowed)

key-decisions:
  - "scp fallback for Windows (no rsync in Git Bash)"
  - "node_args --env-file instead of PM2 env_file (unsupported PM2 feature)"
  - "pm2 delete + start instead of startOrRestart --env production"
  - "provision.sh is idempotent (mkdir -p, apt-get install -y, version guards)"

duration: multi-session
started: 2026-04-02
completed: 2026-04-03
---

# Phase 15 Plan 01: Deploy Nuxt App on LXC — Complete

**PM2 + nginx deployment on LXC 192.168.2.200 — app accessible and healthy**

## Deployment Result

- **URL** : http://192.168.2.200 → HTTP 200 (Nuxt SSR)
- **Health** : http://192.168.2.200/api/health → `{"status":"ok","db":"connected"}`
- **Stack** : Node 22.22.2 + PM2 6.0.14 + nginx 1.22.1
- **DB** : PostgreSQL connected (13 tables, poliscope user)

## Task Commits

1. **Task 1: Create deployment scripts** — `bceb8ce`
2. **Task 2: Deploy to LXC** — verified ✅
3. **Fix: scp fallback + env-file** — post-deploy fix commit

## Issues Encountered & Fixed

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `rsync: command not found` on Windows | Git Bash lacks rsync | Added scp fallback in deploy.sh |
| `Database connection failed` on health | PM2 `env_file` not a real feature | Switched to `node_args: '--env-file=...'` |
| `--env production` PM2 warning | Requires `env_production` section | Changed to `pm2 delete + pm2 start` |
| PG password unknown | Never set/recorded | Reset via ALTER USER |

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| scp fallback over rsync-only | Windows Git Bash lacks rsync; scp universally available |
| `node_args: '--env-file=...'` | PM2 env_file not a real feature; Node 22+ --env-file is native |
| `pm2 delete + pm2 start` | Cleaner restart, no env_production config section needed |
| DB password reset | No existing password known; generated 24-char random |

---
*Completed: 2026-04-03*
