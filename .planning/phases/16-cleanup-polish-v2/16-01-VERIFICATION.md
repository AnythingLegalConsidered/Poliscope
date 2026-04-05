---
phase: 16-cleanup-polish-v2
plan: 01
verified: 2026-04-05T13:40:51Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 16 Plan 01: Verification Report

**Phase Goal:** Corriger la tech debt identifiee par l'audit milestone v2.0 — legacy script, donnees non rendues, badges manquants, sitemap incomplet.
**Verified:** 2026-04-05T13:40:51Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                          | Status     | Evidence                                                                                    |
| --- | ------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------- |
| 1   | run_all.py pipeline executes without referencing non-existent deputies table   | VERIFIED   | Only 3 comment lines reference ingest_deputies.py; no `--skip-deputies` flag; no execution block |
| 2   | Deputy profile page displays vote position breakdown (pour/contre/abstention/absent) | VERIFIED   | `v-if="data.voteStats?.length > 0"` block with French labels and color classes at lines 154-172 |
| 3   | Deputy cards in the grid show an AN or Senat chamber badge                     | VERIFIED   | DeputyCard.vue has optional `chamber` prop + AN/Senat badge spans; index.get.ts selects `actors.chamber`; index.vue spreads via `v-bind="deputy"` |
| 4   | Sitemap includes /votes/:id URLs for all scrutins                              | VERIFIED   | urls.ts queries scrutins in Promise.all, maps to `/votes/${s.id}`, spreads into return array |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `packages/ingestion/scripts/run_all.py` | Pipeline without legacy Step 6 | VERIFIED | Step 6 removed from argparse, steps list, and execution block; 3 comment markers confirming removal |
| `packages/web/app/pages/deputies/[id].vue` | voteStats rendering section | VERIFIED | Lines 154-172: full voteStats block with v-if guard, French labels, position-color mapping |
| `packages/web/app/components/DeputyCard.vue` | Chamber badge display | VERIFIED | `chamber?: string | null` prop at line 5; AN badge (bg-bronze/10) at line 55; Senat badge (bg-ink/10) at line 60 |
| `packages/web/server/api/__sitemap__/urls.ts` | Scrutin URLs in sitemap | VERIFIED | `scrutins` imported from shared/schema; third query in Promise.all; scrutinUrls spread into return |
| `packages/web/server/api/deputies/index.get.ts` | chamber field in deputies list API | VERIFIED | `chamber: actors.chamber` in the select projection at line 50 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `deputies/index.get.ts` | `DeputyCard.vue` | `v-bind="deputy"` spreads chamber prop automatically | WIRED | index.vue line 144: `v-bind="deputy"` passes all fields including `chamber` to DeputyCard; chamber selected in API |
| `deputies/[id].get.ts` | `deputies/[id].vue` | `data.voteStats` consumed by template | WIRED | API computes voteStats (lines 131-143) and returns it (line 149); template consumes at line 154 with `data.voteStats?.length` |
| `__sitemap__/urls.ts` | `pages/votes/[id].vue` | sitemap /votes/:id matches votes page route | WIRED | `pages/votes/[id].vue` exists; sitemap generates matching `/votes/${s.id}` URLs |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
| ----------- | ------ | -------------- |
| ingest_deputies.py retired / run_all.py no longer references non-existent deputies table | SATISFIED | — |
| Deputy profile voteStats rendered in template | SATISFIED | — |
| Parliamentary cards display AN or Senat badge | SATISFIED | — |
| Scrutins appear in sitemap (__sitemap__/urls.ts) | SATISFIED | — |

### Anti-Patterns Found

None detected. No TODO/FIXME/placeholder comments in modified files. No empty implementations. No stub returns. All handlers are real.

### Human Verification Required

#### 1. voteStats rendering on a real deputy profile

**Test:** Open a deputy profile for a deputy with known vote records (e.g. an active AN deputy). Scroll past the tag pills section.
**Expected:** A "Votes" section appears showing colored badges for Pour (green), Contre (red), Abstention (gray), Absent (stone-muted) with counts.
**Why human:** Requires real data in the `votes` table; automated check confirmed the template renders correctly but cannot confirm data flows end-to-end without a running DB.

#### 2. Chamber badge visible on deputy grid cards

**Test:** Navigate to /deputies. Verify that AN deputies show a bronze "AN" badge and Senat deputies show an ink "Senat" badge on each card.
**Expected:** Both badge types visible depending on the deputy's chamber, styled correctly.
**Why human:** Visual appearance and design token rendering (bg-bronze/10, bg-ink/10) can only be confirmed in-browser.

#### 3. Sitemap includes /votes/ URLs

**Test:** Fetch `/sitemap.xml` or `/__sitemap__/urls.json` from the deployed app.
**Expected:** Response includes entries with `loc` values matching `/votes/NNNNN` for scrutin IDs.
**Why human:** Sitemap generation depends on production DB having scrutin rows; cannot verify count without running server.

### Gaps Summary

No gaps. All 4 observable truths are verified. All 5 artifacts are substantive (not stubs), exported, and wired into the application. All 3 key links are confirmed: the API exposes the data, the templates consume it, and the sitemap route matches the votes page route.

The pre-existing TypeScript errors noted in the SUMMARY (drizzle-orm dual-version PgColumn mismatch, Nuxt useFetch union type) are not introduced by this phase and do not affect runtime behavior.

---

_Verified: 2026-04-05T13:40:51Z_
_Verifier: Claude (gsd-verifier)_
