---
phase: 05-profils-deputes
verified: 2026-03-28T00:47:45Z
status: passed
score: 13/13 must-haves verified
re_verification: false
human_verification:
  - test: Navigate to /deputies, type a name in the search box
    expected: List filters to matching deputies, old results clear, no full-page reload
    why_human: Cannot verify reactive watch timing or visual feedback programmatically
  - test: Navigate to /deputies, scroll to the very bottom
    expected: Next page of deputies loads automatically (infinite scroll)
    why_human: IntersectionObserver behavior requires live browser rendering
  - test: Click a deputy card and verify the profile page header
    expected: Photo or initials, name, group badge, constituency all visible
    why_human: External photo URLs and visual layout require browser
  - test: Click a tag pill on a deputy profile, then click it again
    expected: First click filters interventions and highlights pill. Second click clears.
    why_human: Client-side computed filter and visual toggle state require browser
  - test: On a deputy profile, click a debate title above an intervention
    expected: Navigates to /debates/:id for that debate thread
    why_human: Navigation correctness with real data requires live routing
  - test: On a debate thread, click a deputy name in the intervention list
    expected: Navigates to /deputies/:id for that deputy
    why_human: Bidirectional navigation requires live routing from debate context
---
# Phase 05: Profils Deputes — Verification Report

**Phase Goal:** Pages profils avec historique des interventions. Page profil depute (info + stats), Liste des interventions filtrables, Navigation profil <-> debat. Livrable: On peut voir tout ce qu un depute a dit.
**Verified:** 2026-03-28T00:47:45Z
**Status:** PASSED
**Re-verification:** No initial verification
## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can navigate to /deputies from the header nav | VERIFIED | default.vue:10 NuxtLink to /deputies with active-class |
| 2 | User sees a grid of deputy cards with photo, name, group badge, constituency | VERIFIED | deputies/index.vue:101-110 grid renders DeputyCard v-bind; DeputyCard.vue implements all fields |
| 3 | User can search deputies by name | VERIFIED | deputies/index.vue:83-88 v-model search; watch resets list; useFetch passes search to API ilike |
| 4 | User can filter deputies by political group | VERIFIED | deputies/index.vue:89-98 v-model group select with 11 groups; API applies eq filter |
| 5 | User can scroll down to load more deputies (infinite scroll) | VERIFIED | deputies/index.vue:64-72 useIntersectionObserver on sentinel increments page |
| 6 | User can click a deputy card to navigate to their profile | VERIFIED | DeputyCard.vue:25-27 entire card is NuxtLink :to=/deputies/id |
| 7 | User can see deputy info (photo, name, group, constituency) on the profile page | VERIFIED | deputies/[id].vue:84-118 header with img+initials fallback, h1, GroupBadge, constituency |
| 8 | User can see tag distribution stats for the deputy | VERIFIED | deputies/[id].vue:122-135 tag pills from data.tagStats; API computes via SQL groupBy |
| 9 | User can filter interventions by tag on the profile page | VERIFIED | deputies/[id].vue:40-43 filteredInterventions computed; toggle at line 129 |
| 10 | User can see paginated interventions with debate context (title + date) | VERIFIED | deputies/[id].vue:143-154 NuxtLink to debate above each InterventionCard; API LEFT JOINs debates |
| 11 | User can click load more to load additional interventions | VERIFIED | deputies/[id].vue:174-181 Charger plus button increments page; allInterventions accumulator appends |
| 12 | User can click a debate title to navigate to that debate thread | VERIFIED | deputies/[id].vue:145-148 NuxtLink :to=/debates/intervention.debateId |
| 13 | User can click a deputy name in a debate thread to navigate to their profile | VERIFIED | InterventionCard.vue:62-68 NuxtLink :to=/deputies/deputyId when deputyId present |

**Score: 13/13 truths verified**
---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/components/DeputyCard.vue | Deputy card for list display | VERIFIED | 53 lines, NuxtLink wrapper, photo+initials, GroupBadge, constituency |
| app/pages/deputies/index.vue | Deputies list page with search, group filter, infinite scroll | VERIFIED | 136 lines, real useFetch to /api/deputies, IntersectionObserver, accumulator pattern |
| app/layouts/default.vue | Nav link to /deputies | VERIFIED | 18 lines, NuxtLink to /deputies at line 10 with active-class |
| app/pages/deputies/[id].vue | Deputy profile page with stats, tag filter, paginated interventions | VERIFIED | 191 lines, useFetch to /api/deputies/:id, tag pill filter, allInterventions accumulator |
| app/components/InterventionCard.vue | InterventionCard with deputyId prop for profile link | VERIFIED | 78 lines, deputyId optional prop at line 21, conditional NuxtLink at lines 40-41 and 62-68 |
| server/api/deputies/index.get.ts | GET /api/deputies with search/group filter | VERIFIED | 54 lines, real DB query with ilike+eq filters, paginated response |
| server/api/deputies/[id].get.ts | GET /api/deputies/:id with deputy, interventions, tagStats | VERIFIED | 130 lines, real DB queries, LEFT JOIN with debates, SQL groupBy for tagStats |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| deputies/index.vue | /api/deputies | useFetch reactive query params | WIRED | Line 30-34: useFetch with page, limit, search, group all reactive |
| deputies/index.vue | DeputyCard.vue | v-for + v-bind rendering | WIRED | Lines 105-109: DeputyCard v-for over allDeputies |
| DeputyCard.vue | /deputies/:id | NuxtLink | WIRED | Line 26: :to=/deputies/id wraps entire card |
| deputies/[id].vue | /api/deputies/:id | useFetch with reactive page | WIRED | Line 11-14: useFetch with page reactive |
| deputies/[id].vue | /debates/:id | NuxtLink on debate title | WIRED | Lines 145-148: NuxtLink :to=/debates/intervention.debateId |
| InterventionCard.vue | /deputies/:id | NuxtLink when deputyId present | WIRED | Lines 40-41 (avatar) and 62-64 (name): conditional NuxtLink |
| [id].get.ts | Database | Drizzle ORM queries | WIRED | Real SELECT on deputies, interventions, debates, tags; results returned |
---

### Anti-Patterns Found

None. The word placeholder appears in deputies/index.vue lines 86-87 only as an HTML input attribute for search — not a code stub.

---

### Notable Observation: InterventionCard deputy prop on Profile Page

On the profile page, InterventionCard receives v-bind=intervention but enrichedInterventions does not include a deputy sub-object. The prop interface declares deputy: Deputy | null (null accepted) and all accesses use optional chaining. At runtime: speakerName shows, initials avatar from speakerName, no GroupBadge, deputyId nav link present. Acceptable since the deputy context is shown in the profile header. Phase goal is fully met.

---

### Human Verification Required

1. **Search filter reactivity** — Navigate to /deputies, type a name. Expected: list filters, old results clear. Cannot verify reactive timing programmatically.
2. **Infinite scroll trigger** — Navigate to /deputies, scroll to bottom. Expected: next page loads automatically. IntersectionObserver requires live browser.
3. **Profile page visual display** — Click a deputy card. Expected: photo or initials, group badge, constituency shown. External photo URLs and layout require browser.
4. **Tag filter toggle** — Click a tag pill, click again. Expected: filter applied (bronze highlight), cleared on second click. Computed filter and visual state require browser.
5. **Debate title navigation from profile** — Click a debate title above an intervention. Expected: navigates to /debates/:id. Routing correctness requires live navigation.
6. **Bidirectional nav from debate thread** — On /debates/:id, click a deputy name. Expected: navigates to /deputies/:id. Auto-pass of deputyId via v-bind requires live runtime.

---

## Summary

All 13 observable truths are verified against the actual codebase. All 7 key artifacts exist with substantial implementations (no stubs). All 7 key wiring links are confirmed. API endpoints perform real database queries and return correct data shapes. Bidirectional navigation is fully implemented in both directions.

The phase goal is achieved: a user can browse deputies, search and filter by group, open a profile, see all interventions with debate context, filter by topic tag, load more, and navigate bidirectionally between deputy profiles and debate threads.

---

_Verified: 2026-03-28T00:47:45Z_
_Verifier: Claude (gsd-verifier)_
