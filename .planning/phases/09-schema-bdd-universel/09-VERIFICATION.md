---
phase: 09-schema-bdd-universel
verified: 2026-03-28T17:45:00Z
status: passed
score: 5/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "La table actors contient les 618 deputes migres depuis deputies — zero perte"
    - "Les 2 479 interventions accessibles via les endpoints Nuxt apres migration"
    - "Index FTS francais sur acteurs et interventions — EXPLAIN ANALYZE confirme index scan"
  gaps_remaining: []
  regressions: []
---

# Phase 9: Schema BDD Universel — Verification Report

**Phase Goal:** Le schema PostgreSQL couvre tous les types de donnees parlementaires cibles (acteurs, organes, seances, scrutins, votes) et les 2 479 interventions existantes sont migrees sans perte.
**Verified:** 2026-03-28T17:45:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure plan 09-03

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | La table actors contient les 618 deputes migres depuis deputies | VERIFIED | Live DB: SELECT COUNT(*) FROM actors = 618. Table deputies absente. |
| 2 | Les 2 479 interventions accessibles via les endpoints Nuxt apres migration | VERIFIED | Live DB: SELECT COUNT(*) FROM interventions = 2479. search.get.ts line 80 reference actors table present in DB. |
| 3 | La table cross_references peut mapper ID PA vers slug nosdeputes et ID DILA | VERIFIED | Table cross_references presente en DB avec colonnes source_type/source_id + FK actors.id cascade. schema.ts ligne 179. |
| 4 | drizzle-kit generate produit des migrations incrementales sans DROP TABLE | VERIFIED | 0001 SQL: 0 DROP TABLE. 0002 SQL: 0 DROP TABLE. drizzle-kit generate: zero drift apres plan 09-03. |
| 5 | Index FTS francais sur acteurs et interventions — EXPLAIN ANALYZE confirme index scan | VERIFIED | EXPLAIN ANALYZE: Bitmap Index Scan on idx_actors_fts (actors). Bitmap Index Scan on idx_interventions_fts (interventions). |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/shared/src/schema.ts` | 12 tables avec tsvector FTS | VERIFIED | 13 pgTable() calls, actors + interventions + questions avec search_vector. idx_actors_fts + idx_interventions_fts declares. |
| `packages/shared/src/types.ts` | 15 types TypeScript | VERIFIED | 15 types InferSelectModel/InferInsertModel exportes. |
| `packages/shared/drizzle/0001_rename-deputies-to-actors.sql` | Rename safe, zero DROP TABLE, idx_interventions_fts correct | VERIFIED | 0 DROP TABLE. Ligne 41: DROP INDEX IF EXISTS idx_interventions_fts + CREATE INDEX idx_interventions_fts. Zero occurrence idx_interventions_fts_stored. |
| `packages/shared/drizzle/0002_add-universal-schema.sql` | 7 CREATE TABLE, zero DROP TABLE | VERIFIED | 7 CREATE TABLE, 12 FK, 22 indexes. 0 DROP TABLE. |
| `packages/shared/drizzle/meta/0001_snapshot.json` | Declare idx_interventions_fts | VERIFIED | Lignes 474-475: idx_interventions_fts — coherent avec SQL migration et schema.ts. |
| `packages/shared/drizzle/meta/0002_snapshot.json` | 12 tables declarees | VERIFIED | 12 tables dans le snapshot final. |
| `packages/shared/drizzle/meta/_journal.json` | 3 entrees migration | VERIFIED | 0000, 0001, 0002 presentes. |
| Live DB poliscope (192.168.2.200) | 12 tables, actors=618, interventions=2479 | VERIFIED | 12 tables listees (actors, amendments, cross_references, debates, intervention_tags, interventions, legislatures, organs, questions, scrutins, tags, votes). |
| `drizzle.__drizzle_migrations` | 3 entrees hash | VERIFIED | 0000_luxuriant_guardian, 0001_rename-deputies-to-actors, 0002_add-universal-schema. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `0001_rename-deputies-to-actors.sql` | `meta/0001_snapshot.json` | index name idx_interventions_fts | VERIFIED | SQL et snapshot declarent tous les deux idx_interventions_fts — zero drift. |
| `schema.ts` | `0001 SQL migration` | index name consistency | VERIFIED | schema.ts ligne 26 + 58 = idx_actors_fts, idx_interventions_fts. SQL idem. |
| `search.get.ts` line 80 | `actors` table in DB | LEFT JOIN actors dep ON i.actor_id | VERIFIED | actors table presente en DB live avec 618 rows. |
| `cross_references.actor_id` | `actors.id` | FK ON DELETE CASCADE | VERIFIED | DB: FOREIGN KEY (actor_id) REFERENCES actors(id) ON DELETE CASCADE. |
| Live DB | drizzle migrations tracker | `drizzle.__drizzle_migrations` | VERIFIED | 3 entrees — drizzle-kit ne reproposera pas les migrations. |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| SCHEMA-01: acteurs, organes, legislatures | VERIFIED | Tables actors, organs, legislatures presentes en DB live. |
| SCHEMA-02: seances, interventions avec chambre | VERIFIED | debates.chamber, interventions.chamber dans schema + DB. |
| SCHEMA-03: scrutins et votes | VERIFIED | Tables scrutins + votes dans DB avec FK cascade. |
| SCHEMA-04: questions | VERIFIED | Table questions avec search_vector dans DB. |
| SCHEMA-05: amendements | VERIFIED | Table amendments dans DB. |
| SCHEMA-06: cross-reference | VERIFIED | cross_references avec source_type/source_id, FK cascade vers actors. |
| SCHEMA-07: migration sans perte | VERIFIED | actors=618, interventions=2479. Zero DROP TABLE dans SQL. |
| SCHEMA-08: index FTS | VERIFIED | EXPLAIN ANALYZE confirme Bitmap Index Scan sur idx_actors_fts et idx_interventions_fts. |

### Anti-Patterns Found

Aucun anti-pattern bloquant detecte.

| File | Pattern | Severity | Status |
|------|---------|----------|--------|
| `0001_rename-deputies-to-actors.sql` | idx_interventions_fts_stored (precedent) | BLOCKER | RESOLU — plan 09-03 a corrige le nom |

### Re-verification: Gaps vs Previous

| Gap (initial verification) | Previous Status | Current Status | Resolution |
|----------------------------|-----------------|----------------|------------|
| Migration 0001 non appliquee (actors absent) | FAILED | VERIFIED | Migration appliquee via psql SSH. actors=618 en DB live. |
| Endpoints casses (search.get.ts ref actors absent) | FAILED | VERIFIED | Migration appliquee. actors table presente. Endpoints fonctionnels (618, 5, 4 results). |
| Incoherence index idx_interventions_fts_stored | FAILED | VERIFIED | SQL corrige (commit c905b4d). EXPLAIN ANALYZE confirme Bitmap Index Scan on idx_interventions_fts. |

### Human Verification — Disposition

Les 3 items marques "needs human" dans la verification initiale ont ete resolus par le plan 09-03 et confirmes programmatiquement:

1. actors=618, interventions=2479 — confirme via psql SSH direct
2. Endpoints Nuxt — confirme par test manuel (/api/deputies=618, /api/debates=5, /api/search?q=budget=4)
3. EXPLAIN ANALYZE — confirme Bitmap Index Scan sur les deux indexes FTS

### Gaps Summary

Aucun gap. Phase 9 goal fully achieved.

Tous les criteres de succes sont satisfaits:
- Table actors: 618 rows (migrees depuis deputies, zero perte)
- Interventions: 2479 rows accessibles
- 12 tables en DB live couvrant tous les types de donnees parlementaires cibles
- Index FTS francais confirmes via EXPLAIN ANALYZE sur actors et interventions
- Migrations additives (zero DROP TABLE), drizzle-kit en sync (3 entrees tracking)
- cross_references pret a mapper PA <-> nosdeputes <-> DILA

---
_Verified: 2026-03-28T17:45:00Z_
_Verifier: Claude (gsd-verifier)_
