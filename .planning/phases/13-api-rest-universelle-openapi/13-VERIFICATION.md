---
phase: 13-api-rest-universelle-openapi
verified: 2026-04-01T06:20:43Z
status: gaps_found
score: 4/5 must-haves verified
re_verification: false
gaps:
  - truth: Tous les endpoints existants acceptent un parametre chambre (AN/Senat) — les resultats sont filtrables par chambre
    status: partial
    reason: GET /api/debates documente chambre dans OpenAPI (ligne 11) mais lit query.chamber (ligne 21). Le filtre chambre ne fonctionne pas sur /api/debates.
    artifacts:
      - path: packages/web/server/api/debates/index.get.ts
        issue: Mismatch — defineRouteMeta documente name:chambre mais le code lit query.chamber. Le filtre est non fonctionnel.
    missing:
      - Corriger debates/index.get.ts ligne 21 — changer query.chamber en query.chambre pour uniformiser avec /api/votes, OU corriger le defineRouteMeta name:chambre en name:chamber pour uniformiser avec /api/deputies et /api/search
human_verification:
  - test: Acceder a /api/docs dans un navigateur
    expected: Scalar UI affiche tous les 8 endpoints avec leurs parametres documentes
    why_human: Necessite un serveur Nuxt en cours d execution
  - test: GET /api/votes?chambre=AN et GET /api/votes?chambre=Senat
    expected: Resultats filtres par chambre respective, totaux differents
    why_human: Necessite DATABASE_URL avec acces LXC
  - test: GET /api/search?q=budget&type=scrutin
    expected: Retourne uniquement des resultats de type scrutin avec champ type discriminant
    why_human: Necessite base de donnees active
---

# Phase 13: API REST Universelle + OpenAPI — Rapport de Verification

**Phase Goal:** Tous les endpoints API sont stables, documentes, et couvrent les nouvelles donnees (votes, filtre chambre, recherche cross-type) avec une doc Swagger accessible.
**Verified:** 2026-04-01T06:20:43Z
**Status:** gaps_found
**Re-verification:** Non — verification initiale

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Endpoints debats et deputies existants continuent de fonctionner — zero regression | VERIFIED | debates/index.get.ts et [id].get.ts intacts avec defineRouteMeta ajoute; logique DB inchangee |
| 2 | GET /api/votes et GET /api/votes/:id retournent des donnees formatees avec filtre chambre operationnel | VERIFIED | votes/index.get.ts 75 lignes: conditions array, gte/lte, eq(scrutins.chamber), window count, paginatedResponse. [id].get.ts 86 lignes: LEFT JOIN actors, position whitelist, pagination obligatoire |
| 3 | Tous les endpoints acceptent un parametre chambre (AN/Senat) | FAILED | /api/debates: OpenAPI documente chambre mais code lit query.chamber — filtre non fonctionnel sur ce endpoint |
| 4 | La recherche FTS retourne des resultats de type debat et vote dans la meme reponse (cross-type) | VERIFIED | search.get.ts 278 lignes: UNION ALL interventions + scrutins, type discriminant, typeFilter conditionnel, batch tags |
| 5 | Swagger UI accessible a /api/docs — chaque endpoint y est documente | VERIFIED (reserve) | @scalar/nuxt dans modules[], nitro.openAPI route:/api/docs production:runtime, defineRouteMeta dans les 8 endpoints |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| packages/web/server/api/votes/index.get.ts | Votes list avec filtres | VERIFIED | 75 lignes, exports default, real DB query, 4 filtres composables |
| packages/web/server/api/votes/[id].get.ts | Vote detail + per-actor votes | VERIFIED | 86 lignes, LEFT JOIN actors, position whitelist, pagination obligatoire |
| packages/web/server/api/deputies/index.get.ts | Chamber filter added | VERIFIED | chamber condition dans conditions[], defineRouteMeta present |
| packages/web/server/api/deputies/[id].get.ts | voteStats added to profile | VERIFIED | GROUP BY position query, voteStats dans return object |
| packages/web/server/api/search.get.ts | Cross-type UNION ALL search | VERIFIED | 278 lignes, UNION ALL avec branches conditionnelles, type discriminant, batch tags |
| packages/web/nuxt.config.ts | @scalar/nuxt + openAPI config | VERIFIED | modules:[@scalar/nuxt], nitro.openAPI route:/api/docs, production:runtime |
| packages/web/server/api/debates/index.get.ts | Chamber filter + defineRouteMeta | PARTIAL | defineRouteMeta present, mais param name chambre dans OpenAPI vs chamber dans code |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| votes/index.get.ts | DB scrutins | drizzle conditions array | WIRED | eq/gte/lte conditions + and(...conditions), real rows |
| votes/[id].get.ts | DB votes + actors | drizzle LEFT JOIN | WIRED | leftJoin(actors, eq(votes.actorId, actors.id)) |
| deputies/[id].get.ts | DB votes | drizzle GROUP BY position | WIRED | voteStatsRows query + map dans return |
| search.get.ts | DB interventions + scrutins | SQL UNION ALL | WIRED | sql template UNION ALL, db.execute, batch tags |
| nuxt.config.ts | @scalar/nuxt | modules array | WIRED | @scalar/nuxt dans modules[], package.json confirme dependance |
| debates/index.get.ts | DB debates.chamber | eq(debates.chamber, chamber) | BROKEN | Code lit query.chamber mais OpenAPI documente chambre |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| 1. Zero regression sur debats et deputies | SATISFIED | Endpoints intacts, logique DB inchangee |
| 2. GET /api/votes et /api/votes/:id avec filtre chambre | SATISFIED | Implementes avec param chambre correct |
| 3. Tous endpoints acceptent chambre (AN/Senat) | BLOCKED | /api/debates lit chamber mais documente chambre |
| 4. Recherche cross-type debat + vote | SATISFIED | UNION ALL avec type discriminant |
| 5. Swagger UI a /api/docs — tous endpoints documentes | SATISFIED (reserve) | Config presente, verification runtime requise |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| packages/web/server/api/debates/index.get.ts | 11 vs 21 | OpenAPI name:chambre mais code lit query.chamber | BLOCKER | Filtre chambre non fonctionnel sur /api/debates — ?chambre=AN retourne tous les debats |

### Human Verification Required

#### 1. Scalar UI Accessible

**Test:** Lancer pnpm dev depuis packages/web et naviguer vers /api/docs
**Expected:** Scalar UI affiche les 8 endpoints avec leurs parametres et schemas
**Why human:** Necessite un serveur Nuxt actif avec DATABASE_URL valide

#### 2. Filtre Chambre sur /api/votes

**Test:** GET /api/votes?chambre=AN et GET /api/votes?chambre=Senat
**Expected:** Chaque requete retourne uniquement les scrutins de la chambre concernee, totaux differents
**Why human:** Necessite acces a la base de donnees LXC

#### 3. Recherche Cross-type

**Test:** GET /api/search?q=budget puis GET /api/search?q=budget&type=scrutin
**Expected:** Premier retourne un melange avec type:intervention et type:scrutin, second uniquement des scrutins
**Why human:** Necessite base de donnees active

### Gaps Summary

**1 gap bloquant** — Success criteria #3 partiellement echoue.

Le mismatch dans debates/index.get.ts entre le nom de parametre documente dans OpenAPI (chambre, ligne 11) et le nom lu dans le code (chamber, ligne 21) rend le filtre chambre non-fonctionnel sur cet endpoint. Les requetes ?chambre=AN passent sans filtrage et retournent tous les debats.

Les 4 autres endpoints de chambre fonctionnent correctement:
- /api/votes?chambre=AN — OK (nom uniforme dans OpenAPI et code)
- /api/deputies?chamber=AN — OK
- /api/search?chamber=AN — OK

Le correctif est une seule ligne dans debates/index.get.ts: changer query.chamber en query.chambre (ou aligner le defineRouteMeta dans l autre sens).

---

_Verified: 2026-04-01T06:20:43Z_
_Verifier: Claude (gsd-verifier)_
