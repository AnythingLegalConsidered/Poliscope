# Phase 10: Ingestion Acteurs & Organes — Research

**Researched:** 2026-03-28
**Domain:** Python data ingestion — AN + Senat open data APIs, PostgreSQL upsert pipelines
**Confidence:** HIGH (data sources verified, schema inspected, existing code read)

---

## Summary

Phase 10 ingests two chambers of parliamentary actors (577 deputes AN + 348 senateurs) and their organs (commissions permanentes, groupes politiques) into the existing schema. The foundation is already in place: Phase 9 deployed the `actors`, `cross_references`, and `organs` tables with the correct columns, and Phase 2 built the Python ingestion infrastructure (psycopg3, httpx, upsert pattern, config.py, db.py, utils.py).

The critical blocker from STATE.md (Tricoteuses 403) is **resolved**: Tricoteuses migrated from Framagit to `git.en-root.org`, where the data IS accessible under `git.en-root.org/tricoteuses/data/assemblee-brut/AMO10_deputes_actifs_mandats_actifs_organes_XVII/`. Additionally, `data.assemblee-nationale.fr` provides the canonical ZIP downloads and `www.senat.fr/api-senat/senateurs.json` provides the Senate API. The nosdeputes.fr API already used in Phase 2 covers XVIIe legislature deputies but returns only ~77 at a time (partial) — the canonical source for all 577 is the AN open data ZIP.

The main architectural decision is the **ingestion order**: cross_references must be populated after actors (not before — it FK-references actors.id). Organs must be ingested before actor-organ memberships (which are embedded in the mandat data). The correct order is: (1) actors, (2) cross_references, (3) organs, (4) actor-organ memberships.

**Primary recommendation:** Use the AN open data ZIP (`AMO10` for active deputies, `AMO20` for deputies+senators+ministers) as the primary source for AN actors, `www.senat.fr/api-senat/senateurs.json` + `data.senat.fr/data/senateurs/ODSEN_GENERAL.json` for senators. Extend the existing Python pipeline using the same psycopg3 + httpx + upsert pattern from Phase 2.

---

## Data Sources (Verified)

### Assemblee Nationale — Actors

**Primary source (recommended):** AN open data ZIP, legislature 17
- Active deputies with mandates and organs (JSON ZIP, 4.7MB):
  `https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip`
- Contains individual JSON files: `acteurs/PA{ID}.json` and `organes/PO{ID}.json`
- Covers ~577 active AN deputies (XVIIe legislature)
- Updated regularly by the AN

**Alternative source (verified, already used):** nosdeputes.fr API
- URL: `https://www.nosdeputes.fr/deputes/json`
- Returns partial data (~77 entries per response — likely paginated or truncated)
- Already used in Phase 2, but does NOT return all 577 deputies in one call
- Provides slug for photo URL: `https://www.nosdeputes.fr/depute/photo/{slug}/120`
- **Limitation:** nosdeputes.fr is a third-party site; canonical source is data.assemblee-nationale.fr

**Tricoteuses mirror (confirmed accessible as of 2026-03):**
- URL pattern: `https://git.en-root.org/tricoteuses/data/assemblee-brut/AMO10_deputes_actifs_mandats_actifs_organes_XVII/`
- Contains the same data split into individual files (same as AN ZIP, but pre-split)
- Useful for inspection, but downloading individual files per actor is slow
- Recommendation: use the ZIP from data.assemblee-nationale.fr directly

### Assemblee Nationale — Organs

**Same ZIP as actors** (`AMO10` or `AMO20`):
- The ZIP contains both `acteurs/PA*.json` and `organes/PO*.json` files
- Each organ file has: `uid` (e.g., PO59046), `codeType` (COMPER/GP/DELEG/OFFPAR/BUREAU/ASSEMBLEE), `libelle`, `libelleAbrege`, `libelleAbrev`, `viMoDe` (dates), `organeParent`, `chambre`, `legislature`
- No separate download needed — same ZIP has everything

### Senat — Actors

**Primary source (verified):** Live API
- Active senators: `https://www.senat.fr/api-senat/senateurs.json`
- Returns all active senators in one response
- Fields: `matricule` (e.g., "08061X"), `nom`, `prenom`, `civilite`, `serie`, `siege`, `groupe`, `circonscription`, `categorieProfessionnelle`, `organismes[]`

**Alternative source (verified):** Static dataset
- Full JSON: `https://data.senat.fr/data/senateurs/ODSEN_GENERAL.json`
- Fields: `Matricule`, `Qualite`, `Nom_usuel`, `Prenom_usuel`, `Etat` (ACTIF/ANCIEN), `Date_naissance`, `Groupe_politique`, `Commission_permanente`, `Circonscription`, `Courrier_electronique`
- Includes historical senators (Etat=ANCIEN) — filter for ACTIF

**Recommendation:** Use `senateurs.json` (live API) as primary for active senators (simpler, single call). Use `ODSEN_GENERAL.json` to backfill historical data if needed.

### Senat — Organs

**Available datasets at data.senat.fr:**
- Offices & Delegations: `https://data.senat.fr/data/senateurs/ODSEN_OFFDEL.json`
- Study Groups: `https://data.senat.fr/data/senateurs/ODSEN_ETUDES.json`
- Friendship Groups: `https://data.senat.fr/data/senateurs/ODSEN_GIA.json`
- **Note:** These are membership tables, not organ definitions
- Political groups are embedded in each senator's `groupe` field (from senateurs.json) and `Groupe_politique` (from ODSEN_GENERAL.json)

**For Phase 10 scope (commissions + groupes politiques only):** Extract organs from actor data — the `organismes[]` array in `senateurs.json` contains organ codes and types.

---

## Existing Codebase (Phase 2 — Must Build On)

### Current State of actors Table

The `actors` table (renamed from `deputies` in migration 0001) has these columns:
```
id                   INTEGER PK GENERATED ALWAYS AS IDENTITY
official_id          TEXT NOT NULL UNIQUE    -- PA prefix for AN, matricule for Senat
first_name           TEXT NOT NULL
last_name            TEXT NOT NULL
full_name            TEXT NOT NULL
political_group      TEXT
photo_url            TEXT
constituency         TEXT
is_active            BOOLEAN DEFAULT true
actor_type           TEXT NOT NULL DEFAULT 'deputy'  -- 'deputy' | 'senator'
chamber              TEXT                             -- 'AN' | 'Senat'
legislature          INTEGER
search_vector        TSVECTOR GENERATED ALWAYS AS STORED
created_at           TIMESTAMP
updated_at           TIMESTAMP
```

**Existing data:** 618 actors from Phase 2 (deputies from nosdeputes.fr, no chamber/legislature set)

**Migration required:** The 618 existing deputies have `actor_type='deputy'`, `chamber=NULL`, `legislature=NULL`. These must be updated during re-ingestion using the upsert ON CONFLICT on `official_id`.

### current cross_references Table

```
id           INTEGER PK GENERATED ALWAYS AS IDENTITY
actor_id     INTEGER NOT NULL FK actors.id ON DELETE CASCADE
source_type  TEXT NOT NULL    -- 'PA' | 'nosdeputes_slug' | 'dila_href' | 'senat'
source_id    TEXT NOT NULL    -- raw identifier value
created_at   TIMESTAMP
```

**No unique constraint on (actor_id, source_type, source_id)** — must use INSERT ON CONFLICT requiring either adding a unique constraint or using a check-before-insert pattern. **Planner must note this gap.** The upsert pattern needs `ON CONFLICT (actor_id, source_type, source_id)` but that constraint doesn't exist yet. A migration to add `UNIQUE(actor_id, source_type, source_id)` is required for idempotent cross_references ingestion.

### Current organs Table

```
id               INTEGER PK GENERATED ALWAYS AS IDENTITY
official_id      TEXT NOT NULL UNIQUE    -- PO prefix for AN, code for Senat
name             TEXT NOT NULL
short_name       TEXT
organ_type       TEXT NOT NULL           -- 'group' | 'commission' | 'delegation' | 'other'
chamber          TEXT NOT NULL           -- 'AN' | 'Senat'
legislature_id   INTEGER FK legislatures.id
parent_organ_id  INTEGER                 -- no FK constraint (intentional)
start_date       TIMESTAMP
end_date         TIMESTAMP
created_at       TIMESTAMP
```

### Existing Python Infrastructure (packages/ingestion/scripts/)

| File | Purpose | Reuse |
|------|---------|-------|
| `config.py` | DATABASE_URL, REQUEST_DELAY, LEGISLATURE=17 | Keep, add AN_BASE + SENAT_BASE |
| `db.py` | `get_connection()`, `upsert_query()` | Keep as-is |
| `utils.py` | `fetch_json()`, `rate_limit()` | Add `download_zip()` helper |
| `ingest_deputies.py` | Ingests from nosdeputes.fr into `deputies` | Rewrite as `ingest_actors_an.py` |
| `run_all.py` | Orchestrator, runs all scripts | Update for new scripts |

**run_all.py has a bug:** Still references `"deputies"` table in `print_summary()` — must update to `"actors"`.

### Libraries Already Available

From `requirements.txt`:
- `psycopg[binary]>=3.1` — already using psycopg3 with `executemany` pipeline optimization
- `httpx>=0.27` — for HTTP requests (add streaming for ZIP download)
- `python-dotenv>=1.0` — config loading
- `lxml>=5.0` — XML parsing (available if needed)
- `tqdm>=4.60` — progress bars

**No new library installs needed.** The existing stack handles everything:
- ZIP download: `httpx` (streaming) + `io.BytesIO` + `zipfile` (stdlib)
- JSON parsing: `json` (stdlib)
- Batch upsert: `psycopg3.executemany()` (pipeline mode enabled implicitly)

---

## Standard Stack

### Core

| Component | Version/Source | Purpose |
|-----------|---------------|---------|
| psycopg3 | `>=3.1` (already installed) | PostgreSQL connection + batch upsert |
| httpx | `>=0.27` (already installed) | HTTP/ZIP downloads with streaming |
| zipfile | stdlib | In-memory ZIP extraction |
| io.BytesIO | stdlib | In-memory binary buffer for ZIP |
| json | stdlib | Parse individual actor/organ JSON files |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| tqdm | Progress bar for large ingestions | Wrap the actor loop for 577+ items |
| lxml | XML parsing | Only if ZIP contains XML files (AMO10 has JSON ZIPs) |
| logging | Python stdlib | Already used throughout, keep consistent |

### No New Installs Required

All needed libraries are already in `requirements.txt`. No `pip install` step.

---

## Architecture Patterns

### Recommended Script Structure

```
packages/ingestion/scripts/
├── config.py             # UPDATE: add AN_OPENDATA_BASE, SENAT_API_BASE constants
├── db.py                 # KEEP AS-IS
├── utils.py              # UPDATE: add download_and_extract_zip() helper
├── ingest_actors_an.py   # NEW: replaces ingest_deputies.py (AN deputies from ZIP)
├── ingest_actors_senat.py # NEW: senators from senat.fr API
├── ingest_organs_an.py   # NEW: AN organs from same ZIP as actors
├── ingest_organs_senat.py # NEW: Senate organs (groups + commissions) from senat.fr
├── ingest_deputies.py    # KEEP (unchanged, backward compat with Phase 2 data)
├── run_all.py            # UPDATE: orchestrate new scripts in correct order
└── ...
```

**Alternative (simpler):** Combine AN actors + organs into one script since they come from the same ZIP.

### Pattern 1: Download ZIP — Extract in Memory

```python
# Source: httpx docs + zipfile stdlib pattern (verified)
import io
import json
import zipfile
import httpx

def download_and_extract_zip(url: str) -> dict[str, bytes]:
    """Download ZIP, return dict of {filename: content_bytes}."""
    with httpx.Client(timeout=60) as client:
        response = client.get(url)
        response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        return {name: zf.read(name) for name in zf.namelist()}
```

**When to use:** AN open data ZIP downloads (AMO10, AMO20). Avoids writing to disk.

### Pattern 2: Batch Upsert with psycopg3 executemany

```python
# Source: psycopg3 docs — executemany uses pipeline mode implicitly in 3.1+
def upsert_batch(conn, query: str, rows: list[dict]) -> int:
    """Upsert a batch of rows. Returns count."""
    with conn.cursor() as cur:
        cur.executemany(query, rows)
    conn.commit()
    return len(rows)
```

**When to use:** All actor and organ ingestion. Psycopg3 executemany pipeline mode gives significant speedup over per-row execute.

### Pattern 3: Idempotent Cross-References

```python
# Requires UNIQUE(actor_id, source_type, source_id) constraint on cross_references
CROSS_REF_QUERY = """
    INSERT INTO cross_references (actor_id, source_type, source_id)
    VALUES (%(actor_id)s, %(source_type)s, %(source_id)s)
    ON CONFLICT (actor_id, source_type, source_id) DO NOTHING
"""
```

**CRITICAL:** This query requires a unique constraint that does NOT currently exist on cross_references. A migration must add it before this pipeline runs. See Open Questions #1.

### Pattern 4: Map AN Actor JSON to DB Schema

```python
# Source: Verified from PA841657.json and PA795240.json inspection

def map_an_actor(raw: dict) -> dict:
    """Map AN acteur JSON (from ZIP) to actors table columns."""
    uid = raw["uid"]          # e.g., "PA841657"
    civil = raw["etatCivil"]["ident"]

    # Find parliamentary mandate (typeOrgane=ASSEMBLEE)
    mandate = next(
        (m for m in raw.get("mandats", {}).get("mandat", [])
         if m.get("typeOrgane") == "ASSEMBLEE"),
        None
    )

    # Find political group mandate (typeOrgane=GP)
    group_mandat = next(
        (m for m in raw.get("mandats", {}).get("mandat", [])
         if m.get("typeOrgane") == "GP"),
        None
    )

    return {
        "official_id": uid,
        "first_name": civil.get("prenom", ""),
        "last_name": civil.get("nom", ""),
        "full_name": f"{civil.get('prenom', '')} {civil.get('nom', '')}".strip(),
        "political_group": group_mandat.get("organes", {}).get("organeRef") if group_mandat else None,
        "photo_url": None,   # Not in ZIP — must build from slug or nosdeputes
        "constituency": _extract_constituency(mandate),
        "is_active": mandate is not None,
        "actor_type": "deputy",
        "chamber": "AN",
        "legislature": 17,
    }
```

**Note:** The AN ZIP does NOT include photo URLs directly. Photos come from nosdeputes.fr slug or the AN website pattern `https://www2.assemblee-nationale.fr/static/tribun/17/photos/120/{PA_ID}.jpg`.

### Pattern 5: Map Senat Actor JSON to DB Schema

```python
# Source: Verified from www.senat.fr/api-senat/senateurs.json inspection

def map_senat_actor(raw: dict) -> dict:
    """Map senat.fr API senator to actors table columns."""
    return {
        "official_id": raw["matricule"],   # e.g., "08061X"
        "first_name": raw["prenom"],
        "last_name": raw["nom"],
        "full_name": f"{raw['prenom']} {raw['nom']}".strip(),
        "political_group": raw.get("groupe", {}).get("libelle") if raw.get("groupe") else None,
        "photo_url": raw.get("urlAvatar"),  # available in senateurs.json
        "constituency": raw.get("circonscription"),
        "is_active": True,   # senateurs.json = active only
        "actor_type": "senator",
        "chamber": "Senat",
        "legislature": None,   # Senate has no discrete "legislature" concept
    }
```

### Pattern 6: Map AN Organ JSON to DB Schema

```python
# Source: Verified from PO59046.json inspection

ORGAN_TYPE_MAP = {
    "GP": "group",
    "COMPER": "commission",
    "DELEG": "delegation",
    "OFFPAR": "other",
    "BUREAU": "other",
    "ASSEMBLEE": "other",
}

def map_an_organ(raw: dict) -> dict:
    """Map AN organe JSON to organs table columns."""
    code_type = raw.get("codeType", "")
    dates = raw.get("viMoDe", {})
    return {
        "official_id": raw["uid"],         # e.g., "PO59046"
        "name": raw.get("libelle", ""),
        "short_name": raw.get("libelleAbrege") or raw.get("libelleAbrev"),
        "organ_type": ORGAN_TYPE_MAP.get(code_type, "other"),
        "chamber": "AN",
        "legislature_id": None,            # resolve via legislatures table lookup
        "parent_organ_id": None,           # resolve from organeParent field
        "start_date": dates.get("dateDebut"),
        "end_date": dates.get("dateFin"),
    }
```

### Pattern 7: Ingestion Order (Critical for FK Integrity)

```
1. legislatures   (seed if not exists — must exist before organs FK)
2. actors_an      (upsert on official_id)
3. actors_senat   (upsert on official_id)
4. cross_references_an   (PA prefix + nosdeputes_slug)
5. cross_references_senat (senat matricule)
6. organs_an      (from same ZIP as actors)
7. organs_senat   (from senateurs.json organismes)
8. memberships    (actor-organ joins — future, not in Phase 10 scope)
```

### Anti-Patterns to Avoid

- **Downloading individual files per actor from git.en-root.org:** Too slow for 577 actors — use the ZIP.
- **Fetching nosdeputes.fr for all 577 deputies:** The API returns partial data (~77), paginating with no documented page param — unreliable for complete ingestion.
- **Inserting cross_references before actors:** FK will fail. Actors first, always.
- **Not filtering for ACTIF in ODSEN_GENERAL.json:** The dataset includes historical senators (Etat=ANCIEN). Must filter.
- **Assuming mandats.mandat is always a list:** In some actor JSON files it's a dict (single mandate). Use `listify()` helper.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ZIP download + extraction | Custom streaming + temp file | `httpx` + `io.BytesIO` + `zipfile` (stdlib) | 5 lines, in-memory, no disk cleanup |
| Batch upsert | Loop of individual execute() calls | `cur.executemany(query, rows)` | psycopg3 pipeline mode: 5-10x faster |
| Rate limiting | asyncio.sleep loops | `utils.rate_limit()` (already exists) | Already tested and configured |
| DB connection | Manual psycopg3 setup | `db.get_connection()` (already exists) | Already handles DATABASE_URL |
| ON CONFLICT upsert SQL | Manual IF EXISTS logic | `db.upsert_query()` (already exists) | Already generates correct SQL |

**Key insight:** The entire infrastructure already exists. Phase 10 is primarily writing the data mapping functions (`map_an_actor`, `map_senat_actor`, `map_an_organ`) and the ZIP download helper. Do not reimagine the architecture.

---

## Common Pitfalls

### Pitfall 1: mandats.mandat — Dict vs List

**What goes wrong:** When an actor has only ONE mandate, the JSON parser may return a dict instead of a list. Iterating it fails silently or crashes.

**Why it happens:** AN open data XML-to-JSON conversion doesn't normalize single-element arrays.

**How to avoid:**
```python
def listify(v) -> list:
    """Normalize single dict or None to list."""
    if v is None: return []
    if isinstance(v, dict): return [v]
    return v

mandats = listify(raw.get("mandats", {}).get("mandat"))
```

**Warning signs:** `TypeError: string indices must be integers` when accessing mandat fields.

### Pitfall 2: cross_references Table Has No Unique Constraint

**What goes wrong:** Re-running the pipeline inserts duplicate cross-reference rows — upsert ON CONFLICT fails because there's no unique index.

**Why it happens:** Schema was designed with `sourceType + sourceId` but no composite unique constraint was added in migration 0002.

**How to avoid:** Add a migration before Phase 10 ingestion:
```sql
ALTER TABLE cross_references
  ADD CONSTRAINT cross_references_actor_source_unique
  UNIQUE (actor_id, source_type, source_id);
```

**Warning signs:** `duplicate key value violates unique constraint` errors — but only if constraint exists. Without it, silently creates duplicates.

### Pitfall 3: Photo URLs for AN Deputies

**What goes wrong:** The AN open data ZIP does NOT include photo URLs.

**Why it happens:** Photos are served from the AN website directly, not distributed in the open data.

**How to avoid:** Use the pattern `https://www2.assemblee-nationale.fr/static/tribun/17/photos/120/{PA_ID_WITHOUT_PA}.jpg` — e.g., for PA841657 → `841657`. Alternatively, keep using nosdeputes.fr slug-based photos for deputies that existed in Phase 2.

**Warning signs:** All `photo_url` values are NULL after ingestion.

### Pitfall 4: Legislature Seed Required Before Organs FK

**What goes wrong:** The `organs` table has `legislature_id FK legislatures.id`. If the `legislatures` table is empty, organ ingestion fails on the FK.

**Why it happens:** The `legislatures` table was created in migration 0002 but no seed data was provided.

**How to avoid:** Seed the legislature row first, or set `legislature_id=NULL` for organs (the FK is nullable). Recommend seeding:
```sql
INSERT INTO legislatures (number, start_date, chamber)
VALUES (17, '2024-07-08', 'AN')
ON CONFLICT (number) DO NOTHING;
```

**Warning signs:** FK constraint violation on organs insert.

### Pitfall 5: Senat Organs Have Non-Standard IDs

**What goes wrong:** Senate organ codes (from `senateurs.json` `organismes[].code`) are not PO-prefixed. They're alphanumeric codes like "RNCO05" or integers.

**Why it happens:** The Senate and AN have independent naming schemes.

**How to avoid:** Prefix Senat organ IDs with `SENAT_` in `official_id` to avoid collision with AN organ PO-IDs. Or use a separate namespace column. Recommended: `official_id = f"SENAT_{code}"`.

### Pitfall 6: nosdeputes.fr Returns Incomplete XVIIe Data

**What goes wrong:** Phase 2 ingested 618 deputies from nosdeputes.fr. For Phase 10, using the same API returns only ~77 deputies per call.

**Why it happens:** The endpoint likely returns the full legislature eventually but requires pagination or full-dump request.

**How to avoid:** Switch to AN open data ZIP for Phase 10 AN actor ingestion. The ZIP has all 577 active deputies.

### Pitfall 7: Senate Photo URL Field

**What goes wrong:** `urlAvatar` in `senateurs.json` is relative (e.g., `/images/senateurs/48x60/...`) not absolute.

**Why it happens:** The senat.fr API serves relative URLs.

**How to avoid:** Prepend `https://www.senat.fr` to `urlAvatar` values.

---

## Code Examples

### Download and Extract ZIP In Memory

```python
# Source: httpx docs + Python stdlib zipfile — standard pattern
import io
import json
import zipfile
import httpx
from config import REQUEST_DELAY
import time

def download_zip_json_files(url: str) -> dict[str, dict]:
    """
    Download a ZIP from url, return dict of {filename: parsed_json}
    for all .json files in the archive.
    """
    with httpx.Client(timeout=120) as client:
        response = client.get(url)
        response.raise_for_status()

    results = {}
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        for name in zf.namelist():
            if name.endswith(".json"):
                results[name] = json.loads(zf.read(name))

    time.sleep(REQUEST_DELAY)
    return results
```

### Listify Helper (Critical)

```python
def listify(v) -> list:
    """Normalize single dict, list, or None to list."""
    if v is None:
        return []
    if isinstance(v, dict):
        return [v]
    return list(v)
```

### Add unique constraint migration (migration 0003)

```sql
-- Add unique constraint to cross_references for idempotent upsert
ALTER TABLE cross_references
  ADD CONSTRAINT cross_references_actor_source_unique
  UNIQUE (actor_id, source_type, source_id);
```

### Upsert Query for actors (building on db.upsert_query)

```python
# Source: existing db.py upsert_query() pattern
ACTOR_COLUMNS = [
    "official_id", "first_name", "last_name", "full_name",
    "political_group", "photo_url", "constituency", "is_active",
    "actor_type", "chamber", "legislature",
]
query = upsert_query(
    table="actors",
    columns=ACTOR_COLUMNS,
    conflict_column="official_id",
    has_updated_at=True,
)
```

### Filter Active Senators from ODSEN_GENERAL.json

```python
def fetch_active_senators_odsen() -> list[dict]:
    """Fetch all active senators from ODSEN_GENERAL.json."""
    data = fetch_json("https://data.senat.fr/data/senateurs/ODSEN_GENERAL.json")
    # Handle both dict with list and direct list
    if isinstance(data, dict):
        senators = data.get("senateurs", data.get("data", []))
    else:
        senators = data
    return [s for s in senators if s.get("Etat") == "ACTIF"]
```

---

## AN Data ZIP Structure (Verified)

The ZIP `AMO10_deputes_actifs_mandats_actifs_organes.json.zip` contains:
```
json/acteur/PA{ID}.json    -- one file per deputy (~577 files)
json/organe/PO{ID}.json    -- one file per organ (~100-200 files)
```

Each actor file structure (verified from PA841657.json, PA795240.json, PA841047.json):
```json
{
  "uid": "PA841657",
  "etatCivil": {
    "ident": {"civility": "Mme", "prenom": "Anaïs", "nom": "Belouassa-Cherifi", ...},
    "infoNaissance": {...}
  },
  "profession": {"libelleCourant": "..."},
  "uri_hatvp": "https://www.hatvp.fr/...",
  "adresses": {...},
  "mandats": {
    "mandat": [
      {"uid": "PM847549", "typeOrgane": "OFFPAR", "dateDebut": "...", "organes": {"organeRef": "PO..."}},
      {"uid": "PM845946", "typeOrgane": "GP", "dateDebut": "...", "organes": {"organeRef": "PO845514"}},
      {"uid": "PM846330", "typeOrgane": "COMPER", "dateDebut": "...", "organes": {"organeRef": "PO59046"}},
      {"uid": "PM843785", "typeOrgane": "ASSEMBLEE", "dateDebut": "2024-07-07",
       "infoMandat": {"circonscription": "...", ...}}
    ]
  }
}
```

Each organ file structure (verified from PO59046.json):
```json
{
  "uid": "PO59046",
  "codeType": "COMPER",
  "libelle": "Commission de la défense nationale et des forces armées",
  "libelleAbrege": "Défense",
  "libelleAbrev": "CION_DEF",
  "viMoDe": {"dateDebut": "1958-12-09", "dateFin": null},
  "organeParent": {"organeRef": "PO..."},
  "chambre": "AN",
  "legislature": {"organeRef": "PO..."},
  "secretariat": {...}
}
```

---

## Senate API Structure (Verified)

`www.senat.fr/api-senat/senateurs.json` response (verified 2026-03-28):
```json
{
  "senateurs": [
    {
      "matricule": "08061X",
      "nom": "Patriat", "prenom": "François",
      "civilite": "M.", "feminise": false,
      "serie": "2", "siege": 1,
      "url": "https://www.senat.fr/senateur/patriat_francois08061x.html",
      "urlAvatar": "/images/senateurs/48x60/08061x.jpg",
      "twitter": "@...", "facebook": "...",
      "groupe": {"libelle": "RDPI", "ultralibelle": "Rassemblement des démocrates..."},
      "circonscription": "21",
      "categorieProfessionnelle": "57",
      "organismes": [
        {"code": "COMGER", "type": "COMMISSION", "libelle": "Commission des affaires étrangères..."},
        {"code": "ETUDES", "type": "ETUDE", "libelle": "..."},
        ...
      ]
    }
  ]
}
```

`data.senat.fr/data/senateurs/ODSEN_GENERAL.json` (verified 2026-03-28):
```json
[
  {
    "Matricule": "21071F",
    "Qualite": "Mme",
    "Nom_usuel": "Aeschlimann", "Prenom_usuel": "Marie-Do",
    "Etat": "ACTIF",
    "Date_naissance": "1974/04/17",
    "Groupe_politique": "Les Républicains",
    "Type_d_app_au_grp_politique": "Membre du Groupe",
    "Commission_permanente": "commission des affaires sociales",
    "Circonscription": "Hauts-de-Seine",
    "Fonction_au_Bureau_du_Senat": null,
    "Courrier_electronique": "m-d.aeschlimann@senat.fr",
    "PCS_INSEE": "31",
    "Categorie_professionnelle": "Professions libérales",
    "Description_de_la_profession": "Avocat"
  }
]
```

---

## State of the Art

| Old Approach (Phase 2) | New Approach (Phase 10) | Impact |
|------------------------|------------------------|--------|
| nosdeputes.fr API (`/deputes/json`) | AN open data ZIP (`AMO10`) | Complete 577 deputies, canonical source |
| deputies table, official_id = nosdeputes slug | actors table, official_id = PA prefix | Matches AN canonical ID scheme |
| No chamber/legislature fields | chamber='AN', legislature=17 set | Enables multi-chamber queries |
| No cross_references | cross_references with PA + nosdeputes_slug | Enables multi-source ID mapping |
| No senators | senateurs via senat.fr API | Phase success criteria met |
| No organs | organs table from AMO10 ZIP | Commission/group tracking enabled |

**Note on nosdeputes.fr:** Still valuable for photo URLs (slug-based photos). Consider fetching photo URLs from nosdeputes.fr after main ingestion from AN ZIP.

---

## Open Questions

1. **cross_references unique constraint missing**
   - What we know: Table exists but has no UNIQUE(actor_id, source_type, source_id)
   - What's unclear: Whether to add in a new migration 0003 or handle in-script with DELETE + INSERT
   - Recommendation: Add migration 0003 (clean, one line SQL) before ingestion scripts run

2. **Photo URLs for AN deputies from ZIP**
   - What we know: AN ZIP has no photo_url field; nosdeputes.fr has slug-based photos
   - What's unclear: Completeness of nosdeputes.fr photo coverage for all 577 XVIIe deputies
   - Recommendation: Use AN pattern `https://www2.assemblee-nationale.fr/static/tribun/17/photos/120/{id_without_PA}.jpg` — LOW confidence (needs manual test with 1-2 examples before implementing)

3. **AMO20 vs AMO10 for senators**
   - What we know: AMO20 (`dep_sen_min_tous_mandats_et_organes`) includes senators + deputies + ministers
   - What's unclear: Whether the senate part of AMO20 is more complete than senat.fr API
   - Recommendation: Use senat.fr API (`senateurs.json`) for senators — it's authoritative + simpler

4. **legislatures table seed**
   - What we know: Table is empty, organs FK references it
   - What's unclear: Whether to seed in a migration or in the ingestion script
   - Recommendation: Seed in ingestion script with ON CONFLICT DO NOTHING — simpler than a migration

5. **Senat organ IDs namespace collision**
   - What we know: AN uses PO-prefixed IDs, Senate uses non-prefixed codes
   - What's unclear: Exact format of all Senate organ codes in `organismes[].code`
   - Recommendation: Prefix with `SENAT_` in `official_id` — LOW confidence on exact format

---

## Sources

### Primary (HIGH confidence — directly verified)

- `packages/shared/drizzle/0001_rename-deputies-to-actors.sql` — actors table schema
- `packages/shared/drizzle/0002_add-universal-schema.sql` — cross_references, organs schema
- `packages/shared/src/schema.ts` — Drizzle ORM schema definitions
- `packages/ingestion/scripts/ingest_deputies.py` — existing ingestion pattern
- `packages/ingestion/scripts/db.py` — upsert_query helper
- `packages/ingestion/scripts/config.py` — config structure
- `https://git.en-root.org/tricoteuses/data/assemblee-brut/AMO10_deputes_actifs_mandats_actifs_organes_XVII/` — AMO10 structure + individual file inspection (PA841657.json, PA795240.json, PO59046.json)
- `https://www.senat.fr/api-senat/senateurs.json` — Senate live API structure
- `https://data.senat.fr/data/senateurs/ODSEN_GENERAL.json` — Senate general dataset structure
- `https://data.assemblee-nationale.fr/acteurs/deputes-en-exercice` — AN deputy download URLs
- `https://data.assemblee-nationale.fr/acteurs/deputes-senateurs-ministres-de-la-legislature` — AMO20 download URL

### Secondary (MEDIUM confidence)

- `https://www.psycopg.org/psycopg3/docs/api/cursors.html` — executemany vs copy comparison
- `https://data.senat.fr/les-senateurs/` — Senat organ dataset URLs

### Tertiary (LOW confidence — need validation)

- AN photo URL pattern `www2.assemblee-nationale.fr/static/tribun/17/photos/120/{id}.jpg` — inferred from pattern, not directly tested
- Senat organ code format (`SENAT_` prefix recommendation) — based on observed data, exact format unverified for all organs

---

## Metadata

**Confidence breakdown:**
- Data sources & URLs: HIGH — directly verified by fetching live endpoints
- Schema understanding: HIGH — read actual migration SQL and TypeScript schema
- AN actor JSON structure: HIGH — inspected 3 real actor files from Tricoteuses
- Senate actor JSON structure: HIGH — inspected live API + ODSEN_GENERAL
- Organ JSON structure: HIGH — inspected PO59046.json directly
- Architecture pattern: HIGH — builds on existing Phase 2 code
- cross_references constraint gap: HIGH — confirmed by reading migration SQL
- Photo URL patterns: LOW — inferred, needs 1-2 manual tests

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (AN open data ZIP URLs stable; senat.fr API stable)
