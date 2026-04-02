---
phase: 15-deploiement-ops
plan: "01"
subsystem: infra
tags: [nginx, pm2, node22, systemd, rsync, deploy, lxc]

requires:
  - phase: 08-infrastructure
    provides: LXC 192.168.2.200 with PG17, UFW, Debian 12

provides:
  - deploy/provision.sh — one-time LXC setup (Node 22, PM2, nginx, dirs, UFW)
  - deploy/deploy.sh — repeatable local build + rsync + PM2 restart
  - deploy/ecosystem.config.cjs — PM2 process config for Nuxt SSR production
  - deploy/nginx/poliscope.conf — nginx reverse proxy to localhost:3000
  - deploy/.env.production.example — template with NUXT_DATABASE_URL placeholder

affects: [phase-15-plan-02]

tech-stack:
  added: [PM2 5.x, Node.js 22 LTS, nginx (debian bookworm)]
  patterns:
    - Build .output locally, rsync to LXC — no node_modules on server
    - PM2 + systemd startup hook for Node process management
    - nginx reverse proxy on port 80 → Node on port 3000

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
  - "rsync .output instead of git pull + build on LXC — minimal LXC resource usage"
  - "PM2 startOrRestart (not pm2 restart) — handles first deploy when no process exists yet"
  - "env_file in ecosystem.config.cjs loads /opt/poliscope/.env — aligns with Nuxt runtimeConfig NUXT_* prefix convention"
  - "provision.sh is idempotent (mkdir -p, apt-get install -y, version guards)"

patterns-established:
  - "Deploy pattern: pnpm build local → rsync .output → PM2 startOrRestart → pm2 save"

duration: 3min
completed: 2026-04-02
---

# Phase 15 Plan 01: Deploiement LXC Summary

**PM2 + nginx deployment stack for LXC 192.168.2.200 — provision.sh + deploy.sh + ecosystem.config.cjs scripts for repeatable production deploys of the Nuxt 3 SSR app**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-02T06:50:25Z
- **Completed:** 2026-04-02T06:53:00Z (paused at checkpoint)
- **Tasks:** 1/2 (Task 2 awaiting human verification)
- **Files modified:** 6

## Accomplishments

- 4 deployment files created covering the full provision + deploy lifecycle
- Scripts are idempotent and syntactically valid (bash -n passes)
- deploy/.env.production properly excluded from git, .example committed

## Task Commits

1. **Task 1: Create deployment scripts and configs** - `bceb8ce` (chore)
2. **Task 2: Deploy to LXC** — awaiting human-verify checkpoint

**Plan metadata:** (pending — will be committed after Task 2)

## Files Created/Modified

- `deploy/provision.sh` — one-time LXC setup: Node 22 via NodeSource, PM2 global, nginx, directories, UFW 80/tcp, PM2 systemd startup
- `deploy/deploy.sh` — local build + rsync .output + .env + ecosystem.config.cjs to LXC, PM2 restart, health check curl
- `deploy/ecosystem.config.cjs` — PM2 config: poliscope app, /opt/poliscope/.output/server/index.mjs, env_file, max_memory_restart 512M
- `deploy/nginx/poliscope.conf` — nginx server block, proxy_pass to localhost:3000 with WebSocket upgrade headers
- `deploy/.env.production.example` — NUXT_DATABASE_URL + NUXT_SITE_URL template
- `.gitignore` — added `!deploy/.env.production.example` + `deploy/.env.production`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| rsync .output (not build on LXC) | .output is self-contained; LXC has limited RAM, no pnpm needed on server |
| pm2 startOrRestart (not pm2 restart) | restart fails if process doesn't exist yet; startOrRestart is idempotent |
| env_file at /opt/poliscope/.env | PM2 loads env file for the process — NUXT_* vars override runtimeConfig keys |
| --skip-build flag in deploy.sh | Allows iterating deploy without rebuilding when only config changes |
| Abort with exit 1 if .env.production missing | Prevents deploying without DB credentials, prompts operator to fill template |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] .env.production.example was gitignored by .env.* pattern**
- **Found during:** Task 1 (staging files for commit)
- **Issue:** `.env.*` glob in .gitignore blocked `deploy/.env.production.example`; `git add` rejected the file
- **Fix:** Added `!deploy/.env.production.example` negation in .gitignore before the `deploy/.env.production` exclusion
- **Files modified:** .gitignore
- **Committed in:** bceb8ce (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — gitignore interaction)
**Impact on plan:** Essential fix — .example file must be committed to allow new contributors to understand required env vars.

## Issues Encountered

None beyond the gitignore deviation above.

## User Setup Required

Before running Task 2 (deploy), operator must:

1. `cp deploy/.env.production.example deploy/.env.production`
2. Edit `deploy/.env.production` — set `NUXT_DATABASE_URL` with real PostgreSQL password
3. Verify SSH access: `ssh root@192.168.2.200`
4. Clone repo on LXC: `git clone <repo-url> /opt/poliscope/repo` (if not already done)
5. Run provision: `ssh root@192.168.2.200 'bash /opt/poliscope/repo/deploy/provision.sh'`
6. Run deploy from local: `bash deploy/deploy.sh`

## Next Phase Readiness

- Task 2 (human-verify: actual deployment) is pending — app not yet deployed
- After Task 2 approval, Phase 15 Plan 02 (backup + ingestion timers + health endpoint) can begin
- Blocker: SSH access to LXC + real DB password in .env.production required

---
*Phase: 15-deploiement-ops*
*Completed: 2026-04-02 (partial — Task 2 pending)*
