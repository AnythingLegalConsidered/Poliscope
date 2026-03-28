# Requirements: Poliscope

**Defined:** 2026-03-28
**Core Value:** Permettre a n'importe qui de chercher et lire ce qu'un parlementaire a dit sur n'importe quel sujet, en quelques clics.

## v2 Requirements

Requirements for Milestone 2 — Base de Donnees Parlementaire Universelle. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: Le repo est restructure en monorepo pnpm (packages/shared, packages/ingestion, packages/web)
- [ ] **INFRA-02**: Un LXC Debian 12 est provisionne sur PVE02 (4 vCPU, 4 Go RAM, 100 Go disk)
- [ ] **INFRA-03**: PostgreSQL 17 est installe sur le LXC et accessible depuis le dev local
- [ ] **INFRA-04**: Le dev local fonctionne avec `pnpm dev` apres la restructuration monorepo

### Schema

- [ ] **SCHEMA-01**: Le schema BDD couvre acteurs (deputes, senateurs, ministres), organes, legislatures
- [ ] **SCHEMA-02**: Le schema couvre seances, interventions (CRI) avec chambre (AN/Senat)
- [ ] **SCHEMA-03**: Le schema couvre scrutins et votes (position par parlementaire)
- [ ] **SCHEMA-04**: Le schema couvre questions (QAG, ecrites, QOSD) — pret pour ingestion future
- [ ] **SCHEMA-05**: Le schema couvre amendements — pret pour ingestion future
- [ ] **SCHEMA-06**: Une table cross-reference mappe les IDs entre sources (PA, slug, fiche, Senat)
- [ ] **SCHEMA-07**: Les donnees existantes (2 479 interventions, 618 deputes) sont migrees sans perte
- [ ] **SCHEMA-08**: Index FTS francais sur tous les champs texte significatifs

### Ingestion

- [ ] **INGEST-01**: Pipeline acteurs AN (deputes XVIIe) depuis Tricoteuses ou data.assemblee-nationale.fr
- [ ] **INGEST-02**: Pipeline acteurs Senat (senateurs) depuis data.senat.fr
- [ ] **INGEST-03**: Pipeline organes (commissions, groupes politiques AN + Senat)
- [ ] **INGEST-04**: Pipeline CRI AN — toutes les seances XVIIe (~200-300 debats)
- [ ] **INGEST-05**: Pipeline CRI Senat — toutes les seances XVIIe
- [ ] **INGEST-06**: Pipeline scrutins/votes AN (position par depute)
- [ ] **INGEST-07**: Pipeline scrutins/votes Senat
- [ ] **INGEST-08**: Tagging thematique etendu sur les nouvelles interventions
- [ ] **INGEST-09**: Tous les pipelines sont idempotents (re-run safe)

### API

- [ ] **API-01**: Endpoints existants (debates, deputies, search) fonctionnent avec les nouvelles donnees
- [ ] **API-02**: GET /api/votes — liste des scrutins avec filtres (chambre, groupe, date)
- [ ] **API-03**: GET /api/votes/:id — detail d'un scrutin avec positions par parlementaire
- [ ] **API-04**: Filtrage par chambre (AN/Senat) sur tous les endpoints existants
- [ ] **API-05**: Recherche cross-type (debats + votes dans les resultats)
- [ ] **API-06**: Documentation OpenAPI auto-generee avec Swagger UI accessible

### Frontend

- [ ] **UI-01**: Page liste des scrutins/votes avec filtres
- [ ] **UI-02**: Page detail d'un scrutin (qui a vote quoi, visualisation)
- [ ] **UI-03**: Les debats Senat apparaissent dans la liste des debats (filtre chambre)
- [ ] **UI-04**: Profils senateurs (meme UX que deputes)
- [ ] **UI-05**: Navigation bicamerale (toggle/filtre AN/Senat)
- [ ] **UI-06**: Recherche retourne aussi les votes dans les resultats

### Operations

- [ ] **OPS-01**: L'app tourne sur le LXC PVE02 en production
- [ ] **OPS-02**: Backup PostgreSQL automatique (pg_dump cron)
- [ ] **OPS-03**: Cron de refresh donnees hebdomadaire (systemd timer)
- [ ] **OPS-04**: Health check accessible pour monitoring

## v3 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Questions

- **QUEST-01**: Pipeline ingestion QAG (Questions au Gouvernement)
- **QUEST-02**: Pipeline ingestion questions ecrites + reponses
- **QUEST-03**: Pipeline ingestion QOSD
- **QUEST-04**: Page liste/detail questions avec filtres
- **QUEST-05**: Questions dans les resultats de recherche

### Amendements

- **AMEND-01**: Pipeline ingestion amendements (auteur, contenu, sort)
- **AMEND-02**: Page liste/detail amendements avec filtres
- **AMEND-03**: Amendements dans les resultats de recherche

### Dossiers Legislatifs

- **DOSS-01**: Pipeline ingestion dossiers legislatifs (navette)
- **DOSS-02**: Pipeline ingestion CR commissions
- **DOSS-03**: Page dossier avec timeline navette (visualisation)
- **DOSS-04**: Scores d'activite multi-dimensionnels par parlementaire

## Out of Scope

| Feature | Reason |
|---------|--------|
| Legislatures anterieures a XVIIe | Commencer avec donnees propres, etendre plus tard |
| Parlement europeen | Perimetre France uniquement |
| Authentification utilisateur | Donnees publiques, pas de comptes |
| IA / NLP (resumes, sentiment) | Risque confiance + complexite, pas prioritaire |
| Application mobile native | Web responsive suffit |
| Notifications / alertes | Necessite auth + RGPD, hors scope |
| Commentaires utilisateur | Risque moderation (cf. nosdeputes.fr) |
| Real-time websockets | Donnees mises a jour hebdo, pas besoin de temps reel |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 8 | Pending |
| INFRA-02 | Phase 8 | Pending |
| INFRA-03 | Phase 8 | Pending |
| INFRA-04 | Phase 8 | Pending |
| SCHEMA-01 | Phase 9 | Pending |
| SCHEMA-02 | Phase 9 | Pending |
| SCHEMA-03 | Phase 9 | Pending |
| SCHEMA-04 | Phase 9 | Pending |
| SCHEMA-05 | Phase 9 | Pending |
| SCHEMA-06 | Phase 9 | Pending |
| SCHEMA-07 | Phase 9 | Pending |
| SCHEMA-08 | Phase 9 | Pending |
| INGEST-01 | Phase 10 | Pending |
| INGEST-02 | Phase 10 | Pending |
| INGEST-03 | Phase 10 | Pending |
| INGEST-04 | Phase 11 | Pending |
| INGEST-05 | Phase 11 | Pending |
| INGEST-06 | Phase 13 | Pending |
| INGEST-07 | Phase 13 | Pending |
| INGEST-08 | Phase 11 | Pending |
| INGEST-09 | Phase 10 | Pending |
| API-01 | Phase 15 | Pending |
| API-02 | Phase 15 | Pending |
| API-03 | Phase 15 | Pending |
| API-04 | Phase 15 | Pending |
| API-05 | Phase 15 | Pending |
| API-06 | Phase 15 | Pending |
| UI-01 | Phase 16 | Pending |
| UI-02 | Phase 16 | Pending |
| UI-03 | Phase 16 | Pending |
| UI-04 | Phase 16 | Pending |
| UI-05 | Phase 16 | Pending |
| UI-06 | Phase 16 | Pending |
| OPS-01 | Phase 17 | Pending |
| OPS-02 | Phase 17 | Pending |
| OPS-03 | Phase 17 | Pending |
| OPS-04 | Phase 17 | Pending |

**Coverage:**
- v2 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after initial definition*
