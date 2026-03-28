# Poliscope — State

## Current Position
- **Milestone** : 1 — MVP Debats AN
- **Phase** : 5 — Profils Deputes (COMPLETE)
- **Next** : Phase 6 (TBD) or MVP validation
- **Status** : 2/2 plans done

Progress: Phase 5 [██] 2/2 plans done | Overall [█████████████░░] ~13/15 plans

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
| D-0401-01 | Group colors via inline JS (getGroupColor) not CSS variables | Dynamic data per group; CSS variables would be unused/inflexible |
| D-0401-02 | whitespace-pre-wrap in InterventionCard (not v-html) | XSS-safe, handles multiline debate transcript text |
| D-0402-01 | Date in computed with fr-FR + Europe/Paris timezone | Explicit locale and timezone in computed prevents SSR/client hydration mismatch |
| D-0402-02 | useFetch watch: [page] re-fetches automatically | No manual refresh() call needed; avoids double-fetch bugs |
| D-0403-01 | No virtual scrolling on debate thread page | Browser handles ~1000 simple nodes; deferred as premature optimization |
| D-0403-02 | v-bind spread on InterventionCard | API response shape matches component props exactly — no manual binding needed |
| D-0502-01 | deputyId is optional prop on InterventionCard | Existing v-bind spreads auto-pass it; debates API already returns deputyId |
| D-0502-02 | Tag filter client-side on accumulated allInterventions | Simpler UX; resets activeTag to null on page increment |
| D-0502-03 | component :is pattern for conditional NuxtLink avatar | Avoids duplicating full avatar markup in v-if/v-else blocks |
| D-0502-04 | Deputy.fullName typed as string or null | Matches Drizzle/Nuxt SerializeObject<> shape; resolves pre-existing TS2345 |

## Session Continuity
- **Last session**: 2026-03-28
- **Stopped at**: Phase 5 complete (05-02 done)
- **Resume**: Phase 6 planning (if applicable)

## History
- 2026-03-28 : Completed 05-02 — Deputy profile page /deputies/[id] with tag filter, load more, debate context links + InterventionCard deputyId bidirectional nav (commits 2ce1d8d + f7492b4)
- 2026-03-28 : Completed 05-01 — Deputies list page /deputies with search, group filter, infinite scroll + DeputyCard component (commits b8bcd24 + b5cae9b)
- 2026-03-28 : Phase 4 complete — verification PASSED (11/11 must-haves). Design reskin "Marbre & Bronze" applied (commit 06c9e4f)
- 2026-03-28 : Completed 04-03 — debate thread page /debates/[id] with route validation, useFetch, InterventionCard thread, SEO title (commit b93b901)
- 2026-03-28 : Completed 04-02 — DebateCard component + home page with useFetch/useIntersectionObserver infinite scroll (commits 9fb6a35 + f3cde7a)
- 2026-03-28 : Completed 04-01 — @vueuse/core + GroupBadge, InterventionCard, LoadingSpinner + 11-group color system (commits 2e896ad + 5418968)
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
