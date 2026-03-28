---
phase: 07-polish-lancement
plan: 02
subsystem: testing
tags: [e2e, playwright, testing, quality]
dependency_graph:
  requires: ["07-01"]
  provides: ["e2e-test-suite"]
  affects: ["all-pages"]
tech_stack:
  added: ["@playwright/test@1.58.2", "@nuxt/test-utils@4.0.0"]
  patterns: ["data-testid selectors", "Nuxt test-utils Playwright integration"]
key_files:
  created:
    - playwright.config.ts
    - e2e/home.spec.ts
    - e2e/debate.spec.ts
    - e2e/deputies.spec.ts
    - e2e/search.spec.ts
  modified:
    - package.json
    - app/components/DebateCard.vue
    - app/components/DeputyCard.vue
    - app/components/SearchResultCard.vue
    - app/components/InterventionCard.vue
decisions:
  - id: D-0702-01
    decision: "Use @nuxt/test-utils/playwright with Nuxt rootDir integration"
    context: "Ensures tests run against a real Nuxt dev server with full SSR/hydration cycle"
  - id: D-0702-02
    decision: "data-testid selectors on root component elements (not wrappers)"
    context: "Stable selectors that survive CSS class changes; placed on the root element of each card component"
metrics:
  duration: "~10 minutes"
  completed: "2026-03-28"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 11
---

# Phase 7 Plan 02: Playwright E2E Test Suite Summary

**One-liner:** Playwright E2E suite with Nuxt test-utils covering 4 critical user journeys via data-testid selectors across 11 test cases.

## What Was Built

Full Playwright E2E test suite for Poliscope covering all critical user flows before public launch:

- **Playwright setup:** `@playwright/test` + `@nuxt/test-utils` installed, `playwright.config.ts` with Nuxt rootDir integration, Chromium browser installed, `pnpm test:e2e` script
- **data-testid attributes:** Added to all 4 key card components (DebateCard, DeputyCard, SearchResultCard, InterventionCard) for stable CSS-independent selectors
- **4 spec files, 11 tests:** Home page (3 tests), Debate detail (2 tests), Deputies list (3 tests), Search flow (3 tests)

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Playwright setup + data-testid attributes | 6b51669 | playwright.config.ts, package.json, 4 component files |
| 2 | E2E spec files for 4 critical journeys | fdd9da7 | e2e/home.spec.ts, debate.spec.ts, deputies.spec.ts, search.spec.ts |

## Test Coverage

| Spec | Journey | Tests |
|------|---------|-------|
| home.spec.ts | Home page — debates list | loads with cards, infinite scroll, card navigation |
| debate.spec.ts | Debate detail page | title renders, interventions visible, speaker names |
| deputies.spec.ts | Deputies list | loads with cards, search filters, card navigation |
| search.spec.ts | Search flow | header search nav, results page, empty state |

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx playwright test --list` lists 11 tests from 4 files — PASS
- `grep -r "data-testid" app/components/` returns 4 matches — PASS
- `pnpm build` succeeds — PASS (3.46 MB, "Build complete!")
- Tests connect to live Nuxt dev server with DB when `pnpm test:e2e` is run
