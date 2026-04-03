---
phase: 15-deploiement-ops
plan: 02
subsystem: infra
tags: [systemd, postgresql, pg_dump, backup, health, python, drizzle]

# Dependency graph
requires:
  - phase: 15-01
    provides: LXC with app running on PM2, PostgreSQL poliscope DB accessible

provides:
  - system_metadata table (key/value store for pipeline state)
  - migration 0005 for system_metadata
  - /api/health enhanced with last_refresh field
  - daily pg_dump backup via systemd timer (03:00, 30-day retention)
  - weekly ingestion refresh via systemd timer (Mon 02:00)
  - setup-timers.sh for LXC installation

affects: [deploy, ops, health-monitoring, ingestion-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - systemd oneshot services + persistent timers for scheduled tasks
    - system_metadata key/value table for pipeline observability
    - pg_dump piped to gzip for space-efficient backups

key-files:
  created:
    - packages/shared/drizzle/0005_system-metadata.sql
    - deploy/scripts/pg-backup.sh
    - deploy/systemd/pg-backup-poliscope.service
    - deploy/systemd/pg-backup-poliscope.timer
    - deploy/systemd/poliscope-refresh.service
    - deploy/systemd/poliscope-refresh.timer
    - deploy/setup-timers.sh
  modified:
    - packages/shared/src/schema.ts
    - packages/shared/drizzle/meta/_journal.json
    - packages/web/server/api/health.get.ts
    - packages/ingestion/scripts/db.py
    - packages/ingestion/scripts/run_all.py

key-decisions:
  - "poliscope-refresh.service uses ExecStart with venv Python binary directly (no source activate — not valid in systemd ExecStart)"
  - "DATABASE_URL PASSWORD placeholder in poliscope-refresh.service requires manual edit after setup-timers.sh runs"
  - "write_last_refresh only writes on errors==0 (full pipeline success) — partial runs do not update last_refresh"
  - "pg-backup.sh runs as postgres user (owns DB) — backup dir chowned to postgres in setup script"

patterns-established:
  - "system_metadata table: generic key/value for pipeline observability — extensible without schema change"
  - "health endpoint pattern: query DB for metadata alongside connectivity check"

# Metrics
duration: 5min
completed: 2026-04-03
---

# Phase 15 Plan 02: Ops — Backup Timers + Health last_refresh Summary

**Daily pg_dump backup (gzip, 30-day retention) + weekly ingestion timer via systemd, with system_metadata table tracking last_refresh surfaced in /api/health**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-03T07:35:50Z
- **Completed:** 2026-04-03T07:40:54Z
- **Tasks:** 2/2 auto tasks complete (Task 3 = checkpoint:human-verify, paused)
- **Files modified:** 11

## Accomplishments

- system_metadata table added to schema with migration 0005 (key/value, primary key on key column)
- /api/health now queries system_metadata for last_refresh and returns it alongside db status
- run_all.py writes last_refresh timestamp on successful pipeline completion (errors == 0 only)
- Daily pg_dump backup script with 30-day retention, runs as postgres user
- Weekly ingestion refresh via systemd timer (Mon 02:00, Persistent=true)
- setup-timers.sh automates LXC installation: copy scripts, chmod, create dirs, enable timers, create venv if missing

## Task Commits

Each task was committed atomically:

1. **Task 1: system_metadata table + health last_refresh + run_all.py timestamp** - `96610ac` (feat)
2. **Task 2: systemd timers + backup script + setup script** - `fde7a22` (feat)

## Files Created/Modified

- `packages/shared/src/schema.ts` - Added systemMetadata table definition
- `packages/shared/drizzle/0005_system-metadata.sql` - Migration: CREATE TABLE system_metadata
- `packages/shared/drizzle/meta/_journal.json` - Added 0005 entry
- `packages/web/server/api/health.get.ts` - Import eq + systemMetadata, query and return last_refresh
- `packages/ingestion/scripts/db.py` - Added write_last_refresh() function
- `packages/ingestion/scripts/run_all.py` - Import write_last_refresh, call on errors==0
- `deploy/scripts/pg-backup.sh` - pg_dump + gzip + 30-day retention
- `deploy/systemd/pg-backup-poliscope.service` - oneshot, User=postgres
- `deploy/systemd/pg-backup-poliscope.timer` - OnCalendar=*-*-* 03:00:00, Persistent=true
- `deploy/systemd/poliscope-refresh.service` - oneshot, venv python run_all.py, PASSWORD placeholder
- `deploy/systemd/poliscope-refresh.timer` - OnCalendar=Mon *-*-* 02:00:00, Persistent=true
- `deploy/setup-timers.sh` - Full LXC installation script

## Decisions Made

- ExecStart in poliscope-refresh.service uses the venv Python binary directly (`/opt/poliscope/repo/packages/ingestion/.venv/bin/python run_all.py`) — `source activate` is a bash builtin, not valid in systemd ExecStart
- PASSWORD placeholder in poliscope-refresh.service requires manual edit after setup-timers.sh — setup-timers.sh prints a reminder
- write_last_refresh only called when errors == 0 — partial pipeline success should not update last_refresh (would mislead health endpoint)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

After deploying:
1. `bash deploy/deploy.sh` — redeploy app with updated health endpoint
2. Apply migration on LXC: `ssh root@192.168.2.200 "psql -U poliscope -d poliscope -f /opt/poliscope/repo/packages/shared/drizzle/0005_system-metadata.sql"`
3. Pull latest repo: `ssh root@192.168.2.200 "cd /opt/poliscope/repo && git pull"`
4. Run setup: `ssh root@192.168.2.200 "bash /opt/poliscope/repo/deploy/setup-timers.sh"`
5. Edit DB password: `ssh root@192.168.2.200 "nano /etc/systemd/system/poliscope-refresh.service"` then `systemctl daemon-reload`

## Next Phase Readiness

- Task 3 (checkpoint:human-verify) awaits LXC deployment and timer verification
- Paused at checkpoint — resume after confirming timers active and health shows last_refresh

---
*Phase: 15-deploiement-ops*
*Completed: 2026-04-03 (paused at checkpoint)*
