# Poliscope — State

## Current Position
- **Milestone** : 1 — MVP Debats AN
- **Phase** : 3 — API Backend (PLANNED)
- **Next** : Phase 3 execution
- **Status** : 3 plans ready (3 waves)

Progress: Phase 3 [___] 0/3 plans done

## Decisions
| ID | Decision | Context |
|----|----------|---------|
| D-0201-01 | Python 3.12 installed via winget | Was missing from system, needed for scripts |
| D-0201-02 | nosdeputes.fr = 16th legislature | All 618 deputies have mandat_fin, is_active=false correct |
| D-0202-01 | Pivoted from nosdeputes.fr to DILA for debates | nosdeputes.fr /seances/json returns empty for 17th legislature; DILA has CRI XML archives |
| D-0202-02 | DILA CRI XML format: .taz archives | Nested tar with CRI_*.xml, Orateur href for deputy matching |

## Session Continuity
- **Last session**: 2026-03-27
- **Stopped at**: Phase 3 planned, ready for execution
- **Resume**: Phase 3 execution

## History
- 2026-03-27 : Completed 02-03 — Keyword tagging (12 tags, 787 assignments) + pipeline orchestrator (commits 6b8a383 + ea73f54)
- 2026-03-27 : Completed 02-02 — Debate + intervention ingestion from DILA (5 debates, 2479 interventions, commit be82fa2)
- 2026-03-27 : Completed 02-01 — Python env + deputy ingestion (618 deputies, commits fdcb43d + c82a200)
- 2026-03-27 : Phase 2 planned (3 plans, 3 waves) — verified PASS (2 blockers fixed: interventions idempotence strategy, updated_at helper)
- 2026-03-27 : Completed 01-02 — Docker Compose + Drizzle schema + health check API (commit 09a4aae)
- 2026-03-27 : Completed 01-01 — Scaffold Nuxt 4 + Tailwind CSS v4 + project structure (commit 20c8795)
- 2026-03-27 : Phase 1 planned (2 plans, 2 waves) — verified PASS
- 2026-03-27 : Project initialized, planning created
