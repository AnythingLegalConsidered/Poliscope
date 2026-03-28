# Feature Research

**Domain:** Universal parliamentary database — French citizen-facing explorer (AN + Sénat, XVIIe legislature)
**Researched:** 2026-03-28
**Confidence:** HIGH (grounded in competitor analysis of nosdeputes.fr, datan.fr, pappers.fr + official data portals data.assemblee-nationale.fr and data.senat.fr)

---

## Existing Features (Already Built — Milestone 1)

Do not rebuild. These are the foundation for v2 features.

- Debate thread view (CRI AN only)
- Deputy profiles with stats and tag filter
- Full-text search with FTS highlighting + URL sync
- Home page with infinite scroll debates list
- Global header search bar
- SEO (sitemap, meta tags, routeRules caching)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a citizen expects from "a complete parliamentary data site." Missing these = product feels half-done.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Scrutins / votes list** | Every competitor has it (datan.fr, nosdeputes.fr). Citizen asking "did my deputy vote for X?" — core use case. | MEDIUM | Display: date, title, result (pour/contre/abstention), total counts per group. Filter by date, group, type. |
| **Vote detail page** (per scrutin) | Users expect to click a vote and see each deputy's position | MEDIUM | Two views: group summary (pie/bar) + nominative list by group. nosdeputes.fr and datan.fr both do this. |
| **Deputy vote history** (on profil) | Citizens comparing deputies expect this on profile pages | MEDIUM | Depends on vote ingestion. List of scrutins with deputy's position. Already have deputy profile — add tab. |
| **Amendements list** (per dossier) | lafabriquedelaloi.fr, pappers.fr, AN data portal all surface this | MEDIUM | Fields: auteur, objet, sort (adopté/rejeté/tombé), article visé. Filter by sort, auteur, dossier. |
| **Amendement detail page** | Users click to read the full text + reasons | LOW | Display: texte, exposé des motifs, auteur, sort, date dépôt, stade (commission/séance). |
| **Questions (QAG + écrites)** | Users expect to search "what was asked about X" — standard on nosdeputes.fr | MEDIUM | QAG: question + réponse ministre, date, vidéo (lien externe). Questions écrites: question, ministère, réponse (avec délai indicator). |
| **Sénateurs profiles** | Bicameral = users expect symmetry with deputy profiles | MEDIUM | Same structure as deputy profile: interventions, votes, questions, amendements. Sources: data.senat.fr + nossenateurs.fr. |
| **Sénat debates (CRI)** | AN-only = incomplete in a "universal" DB | HIGH | Same ingestion pipeline as AN CRI but from data.senat.fr. Same thread UI reusable. |
| **Dossier législatif page** | Users want to understand what a law went through — lafabriquedelaloi.fr covers this | HIGH | Timeline: dépôt → commission → 1ère lecture AN → 1ère lecture Sénat → navette → adoption. Links to CRI, amendements, votes at each step. |
| **Cross-type full-text search** | Users search a keyword and expect results across all data types | HIGH | Existing FTS infra extends to new tables. Result types: intervention, QAG, question écrite, amendement, CR commission. Type facets in filter UI. |
| **Commissions / CR commissions** | Users interested in committee work — underserved by competitors | MEDIUM | List CR par commission, link to text. Linked to deputies/senators as members. |

### Differentiators (Competitive Advantage)

Features where Poliscope can beat nosdeputes.fr (stale for XVIIe) and datan.fr (votes only, no debates).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Unified actor page** (député + sénateur) | No competitor unifies AN + Sénat with same UI. Citizens don't know which chamber their rep is in. | HIGH | Same page template for député and sénateur. Tabs: Interventions / Votes / Questions / Amendements / Commissions. Indicator: chambre, groupe, circonscription. |
| **Dossier legislatif avec navette visuelle** | lafabriquedelaloi.fr exists but is abandoned/buggy. Gap in market. Citizens need to follow a law across chambers. | HIGH | Timeline component showing AN → Sénat → AN (navette). Each step: link to CRI + amendments + vote. Killer feature for engaged citizens. |
| **Activity score par parlementaire** | datan.fr has participation score (votes only). nosdeputes.fr has global score. Poliscope can compute from ALL types. | MEDIUM | Score = weighted sum: interventions + questions + amendements + présence votes. More honest than vote-only. Displayed on profile. |
| **Type-faceted search UI** | No competitor shows all data types in one search. "Show me everything about immigration: CRI + QAG + amendements" | HIGH | Search results with facets: Interventions / Questions / Amendements / Dossiers. Depends on cross-type FTS. |
| **Bicameral vote comparison** | For laws passing both chambers: show AN vote + Sénat vote side by side | HIGH | Needs dossier linkage + both chambers' scrutins. Unique differentiator. |
| **REST API with OpenAPI docs** | Poliscope becomes infrastructure for other civic tech projects. nosdeputes.fr API is old (XML/CSV, not REST). | MEDIUM | Standard REST endpoints per data type. Swagger/OpenAPI doc auto-generated. Rate limiting. |
| **QOSD (Questions Orales Sans Débat)** | Underserved in all competitors | LOW | Similar to QAG but oral format, no debate. Ingestion from XML. Display: auteur, ministère, date, résumé. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Alertes email / notifications** | Citizens want to "follow" a deputy | Auth system required (out of scope). GDPR. Maintenance burden. | Bookmark URL, RSS feed (stateless, no auth) |
| **Score "d'activité" gamifié** | Users love ranking deputies | Misleading (quantity ≠ quality). Political controversy risk. Methodological attacks. | Show raw counts + let user interpret. Provide methodology page. |
| **Résumé IA des débats** | "Too long, summarize" is common request | LLM cost + quality risk + hallucination in political context. Trust damage. | Good search + headline highlighting (already built). Manual editorial summaries if needed. |
| **Historique des législatures précédentes** | "What did X say in 2017?" | 10x data volume, different schema, quality degradation. Blocks XVIIe completion. | XVIIe first, link to nosdeputes.fr for previous legislatures. |
| **Parlement européen** | Citizens also have MEPs | Completely different data sources, schema, actors. Doubles scope. | French national parliament only for this milestone. |
| **Commentaires citoyens** | "Like nosdeputes" had citizen comments | Moderation burden, auth required, GDPR, spam. nosdeputes.fr comments section is nearly dead. | Link to external discussions (Twitter, media). |
| **Temps réel / live session** | "Show ongoing debates live" | WebSockets complexity, data freshness SLAs, DILA delays. | Cron refresh daily/hourly is sufficient. Show "dernière mise à jour" timestamp. |

---

## Feature Dependencies

```
[Scrutins / Votes list]
    └──requires──> [Vote ingestion pipeline (AN + Sénat)]
                       └──requires──> [Acteurs ingestion (député + sénateur IDs)]

[Vote detail page]
    └──requires──> [Scrutins list]

[Deputy vote history]
    └──requires──> [Vote detail page]
    └──requires──> [Deputy profile (already built)]

[Amendements list]
    └──requires──> [Dossiers législatifs ingestion]
    └──requires──> [Acteurs ingestion]

[Amendement detail]
    └──requires──> [Amendements list]

[Dossier législatif page avec navette]
    └──requires──> [Dossiers ingestion]
    └──requires──> [Scrutins ingestion] (to link votes at each step)
    └──requires──> [Amendements ingestion] (to link amendments at each step)
    └──requires──> [CRI ingestion AN + Sénat] (to link debates at each step)

[Cross-type full-text search]
    └──requires──> [All ingestion pipelines complete]
    └──enhances──> [Existing search page (already built)]

[Unified actor page]
    └──requires──> [Sénateurs ingestion]
    └──enhances──> [Deputy profile (already built)]

[Activity score]
    └──requires──> [All ingestion pipelines]
    └──enhances──> [Unified actor page]

[Bicameral vote comparison]
    └──requires──> [Vote ingestion AN + Sénat]
    └──requires──> [Dossiers législatifs linkage]

[REST API + OpenAPI]
    └──requires──> [Universal DB schema stable]
    └──enhances──> [All data types exposed]
```

### Dependency Notes

- **Acteurs ingestion is the root dependency:** député + sénateur IDs must exist before any typed data (votes, questions, amendements) can be linked to a person.
- **Dossiers législatifs unlocks the most features:** votes, amendements, CRI, and CR commissions can all be contextualized within a dossier once that link exists.
- **Cross-type search requires all pipelines:** defer to final phase. FTS infra (PostgreSQL tsvector) is already built — adding new document types is incremental.
- **Sénat CRI is the highest-effort item:** format differs from AN, volume is large, schema needs validation.

---

## MVP Definition

### Launch With (v1 of this milestone — "Data visible")

The baseline: user can browse all data types, even without cross-links.

- [ ] **Universal schema + acteurs** — député + sénateur in same actors table. Foundation for everything.
- [ ] **Votes / scrutins list + detail** — highest citizen demand, well-understood data format. Datan.fr validates this as primary feature.
- [ ] **Amendements list + detail** — pappers.fr and lafabriquedelaloi.fr validate demand. Per-dossier view.
- [ ] **Questions (QAG + écrites) list + detail** — nosdeputes.fr validates demand. Standard format.
- [ ] **Sénat debates (CRI)** — symmetry with AN debates. Same thread UI reusable.
- [ ] **Sénateurs profiles** — minimal version mirroring deputy profiles.
- [ ] **Updated deputy profiles** — add votes tab + questions tab using new data.

### Add After Validation (v1.x)

- [ ] **Dossiers législatifs with navette timeline** — killer feature, high complexity. Add once base data is stable.
- [ ] **Cross-type full-text search** — depends on all ingestion complete. Extend existing FTS infra.
- [ ] **Activity score** — add to profiles once all data types ingested.
- [ ] **CR Commissions** — niche but complete. Low-effort once schema exists.
- [ ] **QOSD** — small data type, add with questions batch.

### Future Consideration (v2+)

- [ ] **REST API + OpenAPI docs** — deferred to when data is stable. Developer audience secondary to citizen audience.
- [ ] **Bicameral vote comparison** — requires dossiers + both chambers' votes linked. Complex but high value.
- [ ] **RSS feeds** — stateless subscription alternative. Low complexity but low priority.
- [ ] **Previous legislatures (XVIe)** — only after XVIIe is solid.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Universal schema + acteurs ingestion | HIGH (unblocks all) | MEDIUM | P1 |
| Votes / scrutins (list + detail) | HIGH | MEDIUM | P1 |
| Amendements (list + detail) | HIGH | MEDIUM | P1 |
| Questions QAG + écrites | HIGH | MEDIUM | P1 |
| Sénat CRI debates | HIGH | HIGH | P1 |
| Sénateurs profiles | MEDIUM | MEDIUM | P1 |
| Updated deputy profiles (votes + questions tabs) | HIGH | LOW | P1 |
| Dossiers législatifs avec navette | HIGH | HIGH | P2 |
| Cross-type full-text search | HIGH | MEDIUM | P2 |
| Activity score | MEDIUM | LOW (after pipelines) | P2 |
| CR Commissions | MEDIUM | LOW | P2 |
| QOSD | LOW | LOW | P2 |
| REST API + OpenAPI | MEDIUM (dev audience) | MEDIUM | P3 |
| Bicameral vote comparison | HIGH | HIGH | P3 |
| RSS feeds | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for this milestone
- P2: Should have, adds value after core is working
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | nosdeputes.fr | datan.fr | pappers.fr | lafabriquedelaloi.fr | Poliscope (target) |
|---------|---------------|----------|------------|---------------------|-------------------|
| Debates (CRI) | Partial (XVIe only) | No | No | No | AN + Sénat (full XVIIe) |
| Deputy profiles | Yes | Partial | Partial | No | Yes + Sénateurs |
| Votes / scrutins | Yes | Yes (focus) | No | No | Yes (AN + Sénat) |
| Amendements | Partial | No | Yes | Yes (visual) | Yes |
| Questions (QAG) | Yes | No | Yes | No | Yes |
| Questions écrites | No | No | Yes | No | Yes |
| Dossiers législatifs | Partial | No | Partial | Yes (visual) | Yes (navette) |
| CR Commissions | No | No | No | No | Yes |
| Cross-type search | No | No | Partial | No | Yes (FTS) |
| Sénat coverage | nossenateurs.fr separate | No | Partial | Partial | Unified |
| API | Old (XML/CSV) | No | Yes (paid) | No | REST + OpenAPI |
| Design quality | Dated | Good | Good | Abandoned | Modern (marble/bronze) |
| XVIIe coverage | Missing | Yes | Yes | Partial | Full |

**Gap analysis:** The main market gap Poliscope fills is unified AN + Sénat coverage with modern design and cross-type search. nosdeputes.fr is the most complete but stale for XVIIe. datan.fr is vote-focused only. lafabriquedelaloi.fr is the navette reference but abandoned.

---

## Data Types and Expected User Interactions

### Scrutins / Votes
User mental model: "I want to know how deputy X voted on law Y."
- Expected: list view (filterable by date, type, group, result)
- Expected: detail view showing result breakdown by group + nominative list
- Expected: on deputy profile — tab showing all votes with their position
- Expected: on dossier page — embedded vote(s) for this text

### Amendements
User mental model: "I want to see what changes were proposed to law Y, and what survived."
- Expected: list per dossier (filterable by sort: adopté/rejeté, by auteur, by stade)
- Expected: detail with full text + exposé des motifs
- Expected: author linked to deputy/senator profile

### Questions parlementaires
User mental model: "I want to know what questions were asked about immigration / health / etc."
- Expected: QAG — question text + video link (AN provides YouTube links) + response if any
- Expected: Questions écrites — question + ministry + response + delay indicator
- Expected: filterable by ministère, auteur, thème, answered/unanswered

### Dossiers législatifs
User mental model: "I want to follow what happened to law X as it went through parliament."
- Expected: timeline showing all stages (déposé → commission → 1ère lecture → navette → promulgué)
- Expected: at each stage: link to CRI, list of amendements, link to vote
- Expected: current status clearly visible (en cours / adopté / rejeté / caduque)

### CR Commissions
User mental model: "I want to know what was discussed in the defence committee."
- Expected: list per commission (filterable by date, commission name)
- Expected: full text or thread view (same component as CRI debates)

---

## Sources

- [nosdeputes.fr](https://www.nosdeputes.fr/) — feature benchmark (citizen observatory model, activity scores, keywords)
- [datan.fr](https://datan.fr/) — vote-centric features, participation scores, loyalty metrics
- [politique.pappers.fr](https://politique.pappers.fr/) — amendment browsing, questions, legislative monitoring
- [lafabriquedelaloi.fr](https://www.lafabriquedelaloi.fr/) — navette visuelle reference
- [data.assemblee-nationale.fr/travaux-parlementaires](https://data.assemblee-nationale.fr/travaux-parlementaires) — official AN data types: amendements, votes, débats, dossiers
- [data.senat.fr/donnees/](https://data.senat.fr/donnees/) — official Sénat data types: Dosleg, Ameli, Basile-questions, CR
- [nosdeputes.fr API docs](https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/api.md) — existing API patterns for French parliamentary data
- [datan.fr/statistiques/aide](https://datan.fr/statistiques/aide) — methodology for participation and loyalty scores
- [TheyWorkForYou voting analysis](https://votes.theyworkforyou.com/help/about) — reference UX patterns for vote classification
- [Tricoteuses npm package](https://www.npmjs.com/package/@tricoteuses/assemblee) — data structure reference for AN data types

---
*Feature research for: Poliscope v2 — Universal Parliamentary Database (AN + Sénat, XVIIe)*
*Researched: 2026-03-28*
