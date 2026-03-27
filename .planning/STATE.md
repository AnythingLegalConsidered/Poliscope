# Poliscope — State

## Current Position
- **Milestone** : 1 — MVP Debats AN
- **Phase** : 3 — API Backend (COMPLETE)
- **Next** : Phase 4 — Frontend
- **Status** : 3/3 plans done

Progress: Phase 3 [███] 3/3 plans done

## Decisions
| ID | Decision | Context |
|----|----------|---------|
| D-0201-01 | Python 3.12 installed via winget | Was missing from system, needed for scripts |
| D-0201-02 | nosdeputes.fr = 16th legislature | All 618 deputies have mandat_fin, is_active=false correct |
| D-0202-01 | Pivoted from nosdeputes.fr to DILA for debates | nosdeputes.fr /seances/json returns empty for 17th legislature; DILA has CRI XML archives |
| D-0202-02 | DILA CRI XML format: .taz archives | Nested tar with CRI_*.xml, Orateur href for deputy matching |
| D-0301-01 | Use relative imports in server/api (../../db/schema) | Nuxt 4 resolves ~ alias to app/ not project root — breaks server imports |
| D-0301-02 | getPaginationParams takes H3Event directly | Cleaner API, avoids double getQuery() call in handler |
| D-0302-01 | tagStats uses separate GROUP BY query (not in-memory post-process) | Covers all deputy interventions, not just current page |
| D-0302-02 | Interventions in deputy detail ordered by createdAt DESC | Most recent first is natural for profile browsing |
| D-0303-01 | Use db.execute(sql`...`) for FTS query | Drizzle query builder cannot express ts_rank/ts_headline/optional WHERE fragments cleanly |
| D-0303-02 | websearch_to_tsquery over to_tsquery | Handles unescaped user input safely, no manual pre-processing needed |

## Session Continuity
- **Last session**: 2026-03-27
- **Stopped at**: Phase 3, plan 03 complete — Phase 3 done
- **Resume**: Plan Phase 4 (Frontend)

## History
- 2026-03-27 : Completed 03-03 — GET /api/search FTS endpoint with French language, ts_rank, ts_headline highlights (commit 588bcf6)
- 2026-03-27 : Completed 03-02 — GET /api/deputies + GET /api/deputies/:id with tag distribution (commits c176d96 + 478e375)
- 2026-03-27 : Completed 03-01 — Pagination utility + GET /api/debates + GET /api/debates/:id (commits 5446b8d + c79932f)
- 2026-03-27 : Completed 02-03 — Keyword tagging (12 tags, 787 assignments) + pipeline orchestrator (commits 6b8a383 + ea73f54)
- 2026-03-27 : Completed 02-02 — Debate + intervention ingestion from DILA (5 debates, 2479 interventions, commit be82fa2)
- 2026-03-27 : Completed 02-01 — Python env + deputy ingestion (618 deputies, commits fdcb43d + c82a200)
- 2026-03-27 : Phase 2 planned (3 plans, 3 waves) — verified PASS (2 blockers fixed: interventions idempotence strategy, updated_at helper)
- 2026-03-27 : Completed 01-02 — Docker Compose + Drizzle schema + health check API (commit 09a4aae)
- 2026-03-27 : Completed 01-01 — Scaffold Nuxt 4 + Tailwind CSS v4 + project structure (commit 20c8795)
- 2026-03-27 : Phase 1 planned (2 plans, 2 waves) — verified PASS
- 2026-03-27 : Project initialized, planning created
