---
phase: 09-schema-bdd-universel
verified: 2026-03-28T16:30:00Z
status: gaps_found
score: 3/5 must-haves verified
re_verification: false
gaps:
  - truth: "La table actors contient les 618 deputes migres depuis deputies"
    status: failed
    reason: "Migration 0001 non appliquee. DB live: table deputies (618 rows), table actors absente."
    artifacts:
      - path: "packages/shared/drizzle/0001_rename-deputies-to-actors.sql"
        issue: "SQL valide et sans DROP TABLE, mais non execute sur poliscope-db (192.168.2.200)"
    missing:
      - "Corriger incoherence nom index (voir gap 3) AVANT d appliquer la migration"
      - "Appliquer pnpm --filter shared drizzle-kit migrate sur la base live"
  - truth: "Les 2 479 interventions accessibles via endpoints Nuxt apres migration"
    status: failed
    reason: "search.get.ts utilise actors table (SQL line 80) mais DB live a deputies. Endpoints casses."
    artifacts:
      - path: "packages/web/server/api/search.get.ts"
        issue: "Raw SQL reference actors table (line 80) -- DB live has deputies table"
    missing:
      - "Appliquer les migrations 0001 et 0002 sur la base live"
  - truth: "Index FTS francais sur acteurs et interventions -- EXPLAIN ANALYZE confirme index scan"
    status: failed
    reason: "Indexes stored tsvector absents DB live. Incoherence: migration SQL cree idx_interventions_fts_stored mais snapshot/schema.ts declarent idx_interventions_fts."
    artifacts:
      - path: "packages/shared/drizzle/0001_rename-deputies-to-actors.sql"
        issue: "Ligne 41 cree idx_interventions_fts_stored -- nom different du snapshot (idx_interventions_fts)"
      - path: "packages/shared/src/schema.ts"
        issue: "Ligne 58: index idx_interventions_fts -- ne correspond pas a ce que la migration cree"
      - path: "packages/shared/drizzle/meta/0001_snapshot.json"
        issue: "Declare idx_interventions_fts au lieu de idx_interventions_fts_stored"
    missing:
      - "Corriger nom dans SQL migration 0001: idx_interventions_fts_stored -> idx_interventions_fts, et supprimer la ligne DROP INDEX qui deviendrait incorrecte"
      - "Appliquer migrations puis EXPLAIN ANALYZE pour confirmer index scan"
human_verification:
  - test: "Apres correction et application des migrations, verifier counts en DB"
    expected: "SELECT COUNT(*) FROM actors = 618, SELECT COUNT(*) FROM interventions = 2479"
    why_human: "Necessite decision d appliquer la migration en production"
  - test: "Verifier les endpoints Nuxt apres migration"
    expected: "GET /api/deputies retourne 618 acteurs, search endpoint retourne des resultats"
    why_human: "Necessite environnement Nuxt connecte a la base migree"
  - test: "EXPLAIN ANALYZE sur une requete FTS actors"
    expected: "Index Scan using idx_actors_fts confirme"
    why_human: "Necessite base live avec migration appliquee"
---

# Phase 9: Schema BDD Universel -- Verification Report

**Phase Goal:** Le schema PostgreSQL couvre tous les types de donnees parlementaires cibles (acteurs, organes, seances, scrutins, votes) et les 2 479 interventions existantes sont migrees sans perte.
**Verified:** 2026-03-28T16:30:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | La table actors contient les 618 deputes migres depuis deputies | FAILED | DB live: table deputies (618 rows), table actors absente -- migration 0001 non appliquee |
| 2 | Les 2 479 interventions accessibles via endpoints Nuxt apres migration | FAILED | DB live: 2479 interventions existent mais search.get.ts utilise actors (SQL line 80) -- endpoints casses |
| 3 | La table cross_references peut mapper ID PA vers slug nosdeputes et ID DILA | VERIFIED | Schema.ts ligne 179: crossReferences avec sourceType/sourceId pattern |
| 4 | drizzle-kit generate produit des migrations incrementales sans DROP TABLE | VERIFIED | Migration 0001: 0 DROP TABLE. Migration 0002: 0 DROP TABLE. Journal: 3 entrees. |
| 5 | Index FTS francais sur acteurs et interventions -- EXPLAIN ANALYZE confirme index scan | FAILED | DB live: seul idx_interventions_fts (ancien index fonctionnel). Incoherence SQL/snapshot sur nom index. |

**Score:** 3/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| packages/shared/src/schema.ts | 12 tables avec tsvector FTS | VERIFIED | 13 pgTable() calls, actors + interventions + questions avec search_vector, 189 lignes, zero stubs |
| packages/shared/src/types.ts | 15 types TypeScript | VERIFIED | 15 types InferSelectModel/InferInsertModel, tous exportes |
| packages/shared/drizzle/0001_rename-deputies-to-actors.sql | Rename safe, zero DROP TABLE | NOT APPLIED | SQL correct, zero DROP TABLE, mais non execute sur base live |
| packages/shared/drizzle/0002_add-universal-schema.sql | 7 CREATE TABLE, zero DROP TABLE | NOT APPLIED | 7 CREATE TABLE, 12 FK, 22 indexes, zero DROP TABLE -- non applique |
| packages/shared/drizzle/meta/0001_snapshot.json | Snapshot post-migration 0001 | PARTIAL | Declare idx_interventions_fts mais SQL migration cree idx_interventions_fts_stored |
| packages/shared/drizzle/meta/0002_snapshot.json | Snapshot post-migration 0002 | VERIFIED | 12 tables declarees dans le snapshot final |
| packages/shared/drizzle/meta/_journal.json | 3 entrees de migration | VERIFIED | Entrees: 0000, 0001, 0002 presentes |
| packages/web/server/db/schema.ts | DOIT ETRE SUPPRIME | VERIFIED | Fichier supprime -- plus de doublon local |
| API routes (6 fichiers) | Importent depuis shared/schema | PARTIAL | 5/6 routes importent shared/schema. search.get.ts raw SQL mais reference actors table absente en DB live |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| deputies/index.get.ts | actors table | import shared/schema + Drizzle ORM | WIRED (schema) / BROKEN (DB) | Query sur actors mais DB a deputies |
| search.get.ts | actors table | raw SQL LEFT JOIN actors dep ON i.actor_id | WIRED (schema) / BROKEN (DB) | Table actors absente en DB live |
| cross_references | actors FK cascade | schema.ts ligne 181: actorId FK actors.id onDelete cascade | VERIFIED (schema) | Defini correctement |
| votes | scrutins + actors | FK cascade dans schema + migration 0002 | VERIFIED (schema) | votes->scrutins cascade, votes->actors cascade |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| SCHEMA-01: acteurs, organes, legislatures | VERIFIED (schema) | Migration non appliquee |
| SCHEMA-02: seances, interventions avec chambre | VERIFIED (schema) | debates.chamber, interventions.chamber presentes |
| SCHEMA-03: scrutins et votes | VERIFIED (schema) | Tables scrutins + votes avec FK cascade |
| SCHEMA-04: questions | VERIFIED (schema) | Table questions avec search_vector FTS |
| SCHEMA-05: amendements | VERIFIED (schema) | Table amendments definie |
| SCHEMA-06: cross-reference | VERIFIED (schema) | cross_references avec sourceType/sourceId pattern |
| SCHEMA-07: migration sans perte | PARTIAL | SQL correct (zero DROP TABLE) mais migration non appliquee |
| SCHEMA-08: index FTS | PARTIAL | Definis dans schema + SQL, mais non appliques + incoherence nom index |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| 0001_rename-deputies-to-actors.sql | 41 | Cree idx_interventions_fts_stored | BLOCKER | Snapshot/schema.ts declarent idx_interventions_fts -- drift drizzle-kit apres migration |
| meta/0001_snapshot.json | 474 | Declare idx_interventions_fts | BLOCKER | Incoherence avec SQL de migration -- a corriger avant d appliquer |

### Human Verification Required

#### 1. Correction incoherence index puis application des migrations

**Test:** Corriger le nom d index, executer pnpm --filter shared drizzle-kit migrate, verifier SELECT COUNT(*) FROM actors et SELECT COUNT(*) FROM interventions.
**Expected:** actors: 618, interventions: 2479 -- sans perte de donnees
**Why human:** Necessite decision d appliquer la migration en production

#### 2. Verification endpoints Nuxt apres migration

**Test:** Apres migration, tester GET /api/deputies, GET /api/debates/[id], GET /api/search?q=budget
**Expected:** Zero erreur 500, reponses avec donnees correctes
**Why human:** Necessite environnement Nuxt connecte a la base migree

#### 3. EXPLAIN ANALYZE sur index FTS

**Test:** EXPLAIN ANALYZE SELECT id FROM actors WHERE search_vector @@ to_tsquery('french', 'ministre')
**Expected:** Index Scan using idx_actors_fts confirme
**Why human:** Necessite base live avec migration appliquee

### Gaps Summary

Phase 9 a produit un travail de definition de schema de haute qualite: 12 tables bien definies, migrations additives sans DROP TABLE, 15 types TypeScript, API routes recablees vers shared/schema. La logique est solide.

Deux blocages empechent la validation du goal:

**Blocage 1 -- Migrations non appliquees (criteres 1, 2, 5):** Les migrations SQL 0001 et 0002 n ont pas ete executees sur la base live poliscope-db (192.168.2.200). La base conserve la structure d avant-Phase-9 (5 tables, table deputies). Tous les endpoints Nuxt qui referencent actors sont casses en production.

**Blocage 2 -- Incoherence de nom d index interventions FTS (critere 5, bloquant avant deploy):** La migration SQL 0001 ligne 41 cree idx_interventions_fts_stored, mais le snapshot drizzle (0001_snapshot.json ligne 474) et schema.ts (ligne 58) declarent idx_interventions_fts. Apres application de la migration, drizzle-kit generate detectera un drift et proposera une migration parasite. Cette incoherence doit etre corrigee AVANT l application des migrations.

**Correction recommandee pour Blocage 2:** Dans packages/shared/drizzle/0001_rename-deputies-to-actors.sql, remplacer idx_interventions_fts_stored par idx_interventions_fts (ligne 41). Supprimer la ligne 44 (DROP INDEX IF EXISTS "idx_interventions_fts") qui supprimerait sinon le bon index. Aucune mise a jour du snapshot necessaire -- le snapshot declare deja idx_interventions_fts.

---
_Verified: 2026-03-28T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
