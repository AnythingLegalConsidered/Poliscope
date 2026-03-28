---
phase: 08-monorepo-infra-lxc
plan: 01
subsystem: infra
tags: [pnpm, monorepo, nuxt, drizzle, python, workspace]

# Dependency graph
requires:
  - phase: 07-seo-e2e
    provides: Nuxt app with E2E suite to be restructured into monorepo
provides:
  - pnpm monorepo with packages/shared, packages/web, packages/ingestion
  - Drizzle schema extracted to shared package with workspace:* resolution
  - Root pnpm scripts delegating via --filter to each package
affects: [08-02-lxc-ansible, 09-cross-ref, 10-deputes-ingestion, all future phases]

# Tech tracking
tech-stack:
  added: [pnpm workspaces, pnpm-workspace.yaml, .npmrc shamefully-hoist]
  patterns:
    - Monorepo: packages/shared exports schema via TypeScript source (no build step)
    - Python config.py loads .env 3 levels up from packages/ingestion/scripts/
    - Root package.json contains only pnpm --filter delegation scripts

key-files:
  created:
    - pnpm-workspace.yaml
    - .npmrc
    - packages/shared/package.json
    - packages/shared/src/schema.ts
    - packages/shared/src/index.ts
    - packages/shared/drizzle.config.ts
    - packages/web/package.json
    - packages/ingestion/package.json
    - packages/ingestion/scripts/config.py
    - .env.example
  modified:
    - package.json (rewritten as monorepo root)
    - packages/web/server/utils/db.ts (import from shared/schema)
    - packages/web/playwright.config.ts (LXC_IP placeholder)
    - .gitignore (Python + test-results entries)
    - pnpm-lock.yaml (regenerated with workspace resolution)

key-decisions:
  - "shared package exports TypeScript source directly via exports field — no build step needed (Vite resolves .ts in monorepo)"
  - "shamefully-hoist=true in .npmrc — required for Nuxt auto-imports to resolve workspace deps"
  - "packages/web/server/db/schema.ts kept as copy (renamed) — canonical schema now in packages/shared/src/schema.ts"

patterns-established:
  - "Import shared types: import * as schema from 'shared/schema' (not relative path)"
  - "Python scripts: cd scripts && python — bare imports preserved, .env path is 3 levels up"
  - "DB commands: pnpm db:generate delegates to pnpm --filter shared db:generate"

# Metrics
duration: 20min
completed: 2026-03-28
---

# Phase 8 Plan 01: Monorepo Restructure Summary

**pnpm monorepo with packages/shared (Drizzle schema), packages/web (Nuxt 4), and packages/ingestion (Python) — pnpm build passes with workspace:* resolution**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-28T13:27:33Z
- **Completed:** 2026-03-28T13:47:00Z
- **Tasks:** 2/2
- **Files modified:** 70+

## Accomplishments

- Created pnpm workspace with three packages: shared, web, ingestion
- Extracted Drizzle schema + migration files from server/db/ into packages/shared/
- Moved entire Nuxt app (app/, server/, e2e/, public/) into packages/web/
- Moved Python scripts into packages/ingestion/scripts/ with updated .env path
- pnpm install + pnpm build both succeed — Vite resolves `shared/schema` workspace import
- Removed docker-compose.yml and docker/ (locked M2 decision)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create packages/shared and extract Drizzle schema** - `1576883` (chore)
2. **Task 2: Move Nuxt app to packages/web and Python to packages/ingestion** - `df86302` (chore)

## Files Created/Modified

- `pnpm-workspace.yaml` — workspace declaration for packages/*
- `.npmrc` — shamefully-hoist=true for Nuxt auto-import compatibility
- `packages/shared/src/schema.ts` — Drizzle schema (moved from server/db/schema.ts)
- `packages/shared/src/index.ts` — re-exports schema + types
- `packages/shared/drizzle.config.ts` — schema path updated to ./src/schema.ts
- `packages/web/package.json` — Nuxt package with shared workspace:* dep
- `packages/web/server/utils/db.ts` — updated import from 'shared/schema'
- `packages/web/playwright.config.ts` — LXC_IP placeholder for test DB URL
- `packages/ingestion/scripts/config.py` — .env path 3 levels up
- `packages/ingestion/package.json` — ingest scripts using cd scripts && python
- `package.json` — rewritten as monorepo root with pnpm --filter delegation
- `.env.example` — updated with LXC placeholders

## Decisions Made

- Shared package exports TypeScript source directly via `exports` field — Vite resolves `.ts` at build time, no transpile step needed
- `shamefully-hoist=true` required — Nuxt auto-imports scan node_modules heuristically and need packages hoisted
- Kept `packages/web/server/db/schema.ts` as git-renamed copy (for reference) — canonical source is now `packages/shared/src/schema.ts`

## Deviations from Plan

None — plan executed exactly as written. The `pnpm install` required `CI=true` env + manual `rm -rf node_modules` due to Windows file locking on binary files, but this is a Windows environment quirk, not a plan deviation.

## Issues Encountered

- `pnpm install` initial run failed with `EPERM: operation not permitted` on `@rollup/rollup-win32-x64-msvc.node` (locked binary). Fixed by removing node_modules first (`rm -rf node_modules`) then re-running install. Standard Windows/pnpm behavior when restructuring node_modules layout.

## User Setup Required

None — no external service configuration required. Update `.env` with LXC_IP when Ansible provisioning (08-02) completes.

## Next Phase Readiness

- Monorepo structure complete — packages/shared, packages/web, packages/ingestion all wired
- pnpm build succeeds — ready for 08-02 LXC provisioning continuation
- Python scripts in packages/ingestion/ — ready for future ingestion phases (10+)
- DB schema in shared/ — ready for schema evolution in phase 09+

## Self-Check: PASSED

All files verified present. Both task commits confirmed in git log.

| Check | Result |
|-------|--------|
| pnpm-workspace.yaml | FOUND |
| .npmrc | FOUND |
| packages/shared/src/schema.ts | FOUND |
| packages/web/package.json | FOUND |
| packages/web/server/utils/db.ts | FOUND |
| packages/ingestion/scripts/config.py | FOUND |
| SUMMARY.md | FOUND |
| Commit 1576883 | FOUND |
| Commit df86302 | FOUND |

---
*Phase: 08-monorepo-infra-lxc*
*Completed: 2026-03-28*
