---
phase: 01-setup-infrastructure
plan: 02
subsystem: database, docker, api
tags: [postgresql, drizzle, docker-compose, health-check]
dependency_graph:
  requires: [01-01]
  provides: [docker-compose, drizzle-schema, health-api, db-scripts]
  affects: [all-future-plans]
tech_stack:
  added: [postgres:17-alpine, drizzle-orm, docker-compose]
  patterns: [nitro-auto-imports, runtime-config-env-mapping, french-fts]
key_files:
  created:
    - docker-compose.yml
    - docker/Dockerfile.dev
    - server/db/schema.ts
    - server/utils/db.ts
    - server/api/health.get.ts
    - drizzle.config.ts
  modified:
    - package.json
decisions: []
metrics:
  duration: 231s
  completed: 2026-03-27
---

# Phase 1 Plan 2: Docker Compose + Drizzle Schema + Health Check Summary

Docker Compose with PostgreSQL 17 and Nuxt dev service, Drizzle ORM schema (5 tables with French full-text search), and GET /api/health endpoint confirming DB connectivity.

## What Was Done

### Task 1: Docker Compose + Drizzle schema + DB connection
- Created `docker-compose.yml` with `db` (postgres:17-alpine) and `app` (Nuxt dev) services
- Created `docker/Dockerfile.dev` for development container
- Created `server/db/schema.ts` with 5 tables: deputies, debates, interventions, tags, intervention_tags
- Full-text search GIN index on interventions.content using French config
- Created `server/utils/db.ts` with Drizzle client (auto-imported by Nitro)
- Created `drizzle.config.ts` for drizzle-kit CLI
- Created `.env` (gitignored) with DATABASE_URL for local drizzle-kit usage

### Task 2: Health check API + npm scripts + verification
- Created `server/api/health.get.ts` returning `{"status":"ok","db":"connected","timestamp":"..."}`
- Added npm scripts: `db:push`, `db:generate`, `db:migrate`, `db:studio`
- Verified hybrid mode (docker db + local nuxt): health endpoint returns 200
- Verified 5 tables exist in PostgreSQL
- Verified French FTS: `to_tsvector('french', 'les interventions du depute')` returns correct tsvector

## Must-Haves Verification

| Must-Have | Status |
|-----------|--------|
| docker compose up db lance PostgreSQL accessible sur localhost:5432 | PASS |
| GET /api/health retourne { status: 'ok', db: 'connected' } | PASS |
| Les tables deputies, debates, interventions, tags, intervention_tags existent | PASS |
| docker compose up lance l'app complete (Nuxt + PostgreSQL) | PASS (config verified) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created .env file for drizzle-kit**
- **Found during:** Task 1
- **Issue:** drizzle-kit needs DATABASE_URL env var but Nuxt uses NUXT_DATABASE_URL mapping. drizzle.config.ts uses `dotenv/config` which needs a .env file.
- **Fix:** Created `.env` with `DATABASE_URL=postgresql://poliscope:poliscope_dev@localhost:5432/poliscope` (already in .gitignore)
- **Files created:** .env

**2. [Rule 3 - Blocking] Docker Desktop not running**
- **Found during:** Task 1 verification
- **Issue:** Docker daemon was not running on the host
- **Fix:** Started Docker Desktop programmatically, waited for daemon readiness
- **Impact:** None (normal dev environment state)

## Commits

| Commit | Message |
|--------|---------|
| 09a4aae | feat(phase-1): Docker Compose + Drizzle schema + health check API |

## Self-Check: PASSED

All 6 created files verified. Commit 09a4aae verified.
