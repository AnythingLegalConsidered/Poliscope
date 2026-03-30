# Phase 11: Ingestion Debats CRI — Research

**Researched:** 2026-03-30
**Domain:** Python data ingestion — CRI XML (AN + Senat), PostgreSQL upsert, actor matching
**Confidence:** HIGH (data sources verified by direct HTTP + XML inspection, schema read directly)

---

## Summary

Phase 11 ingests all public plenary sessions (seances publiques) of the XVIIe legislature for both the Assemblee Nationale (~200-300 sessions) and the Senat (~200 sessions) into the `debates` + `interventions` tables, then applies thematic tagging to new interventions.

**Two distinct work streams:**

**Stream 1 (11-01):** The existing `ingest_debates.py` already works against the DILA AN .taz source but references the old `deputies` table and `deputy_id` column — both renamed in migration 0001. The script needs refactoring to use `actors`/`actor_id`, and speaker matching needs to use `cross_references` for more reliable ID lookup. The full XVIIe legislature scope (2024-2026) is already covered by the existing year list.

**Stream 2 (11-02):** A new `ingest_debates_senat.py` must be written. The Senat CRI is available as a bulk ZIP download at `https://data.senat.fr/data/debats/cri.zip` (510 MB, last modified 2026-03-30 — live data). The XML format is a custom DILA format (NOT Akoma Ntoso — confirmed by inspection), structurally similar to the AN CRI but with different element names: `PublicationDSenat` root, `<Orateur><Nom>` for speaker name, `<Qualite>` for role, `<Para>` for content. Files are per-session with filename pattern `SEN_YYYYMMDD_NNN.xml`. The tagging pipeline (`tag_interventions.py`) already works chamber-agnostically on `interventions.content` and requires no changes beyond being run after both ingestion scripts.

**Primary recommendation:** Refactor `ingest_debates.py` to use `actors`/`actor_id`, then write `ingest_debates_senat.py` following the same structural pattern with cri.zip as source. Both scripts must set `chamber` on debates and interventions. Tagging runs unchanged at end.

---

## Data Sources (Verified)

### Assemblee Nationale — CRI

**Source (already working):** DILA OPENDATA
- Base URL: `https://echanges.dila.gouv.fr/OPENDATA/Debats/AN/`
- Structure: yearly directories `2024/`, `2025/`, `2026/`
- Files: `AN_{PARUTION}.taz` per session (e.g., `AN_2025001.taz`)
- Archive: `.taz` = nested tar (outer tar → inner tar → `CRI_*.xml`)
- XVIIe legislature: years 2024, 2025, 2026 (already default in existing code)
- Volume: ~200-300 sessions total for XVIIe legislature

**XML Structure (existing code already parses):**
```xml
<root>
  <Metadonnees><LegislatureNumero/><SessionNom/><DateParution/></Metadonnees>
  <CompteRendu>
    <Metadonnees><dateSeance/><numSeance/></Metadonnees>
    <Quantiemes><Journee/></Quantiemes>
    <Contenu>
      <Para>
        <Orateur href="http://...fiches_id/795746.asp">
          <Nom>M. Nom Prénom,</Nom>
        </Orateur>
        <QualiteMouvement>Premier ministre</QualiteMouvement>
        ...speech text...
      </Para>
    </Contenu>
  </CompteRendu>
</root>
```

Speaker matching: `href` attribute contains fiche ID (e.g., `795746`) — maps to `official_id` in `actors` table (PA prefix stripped). Fallback: normalized name match.

### Senat — CRI

**Source (verified):** data.senat.fr bulk download
- URL: `https://data.senat.fr/data/debats/cri.zip`
- Size: 510 MB compressed (last-modified: 2026-03-30 — updated daily)
- Content: all CRI XML since January 2003, including full XVIIe legislature
- License: open data (data.senat.fr license)

**Archive structure inside cri.zip:** individual XML files per session named `SEN_YYYYMMDD_NNN.xml`

**XML Structure (verified by downloading + inspecting `SEN_20130116_001.taz`):**
```xml
<PublicationDSenat xmlns:xsi="...">
  <Metadonnees>
    <typePublication>DEBAT_SENAT</typePublication>
    <dateParution>2013-01-16+01:00</dateParution>
    <numParution>1</numParution>
    <dateSeance>2013-01-15+01:00</dateSeance>
    <numSeance>45</numSeance>
    <session>
      <periode><dateACompterDu/><dateJusquau/></periode>
      <sessionOrd>session ordinaire</sessionOrd>
    </session>
  </Metadonnees>
  <ContenuDSenat>
    <CompteRendu>
      <Contenu>
        <PresidentSeance>PRÉSIDENCE DE MME BARIZA KHIARI
          <QualitePresident>vice-présidente</QualitePresident>
        </PresidentSeance>
        <!-- Summary section (Sommaire) then actual content sections -->
        <Section>
          <TitreStruct><Intitule>SECTION TITLE</Intitule></TitreStruct>
          <Para Ident="SNCR...">
            <Orateur>
              <Nom>M. François Marc.</Nom>
              <!-- No href on Senat Orateur — speaker identified by name only -->
            </Orateur>
            Speech content here...
          </Para>
          <Para Ident="SNCR...">
            <Orateur>
              <Nom>M. Alain Vidalies, </Nom>
              <Qualite>ministre délégué auprès du Premier ministre, chargé des relations avec le Parlement.</Qualite>
            </Orateur>
            Speech content here...
          </Para>
        </Section>
      </Contenu>
    </CompteRendu>
  </ContenuDSenat>
</PublicationDSenat>
```

**Key differences from AN XML:**
| | AN CRI | Senat CRI |
|-|--------|-----------|
| Root element | varies | `PublicationDSenat` |
| Session date | `<dateSeance>` in `CompteRendu/Metadonnees` | `<dateSeance>` in root `Metadonnees` |
| Session number | `<numSeance>` | `<numSeance>` |
| Session title | `<Journee>` in Quantiemes | `<PresidentSeance>` / session sections |
| Speaker name | `<Orateur><Nom>` | `<Orateur><Nom>` (same) |
| Speaker role | `<QualiteMouvement>` child of Para | `<Qualite>` child of `<Orateur>` |
| Speaker ID | `href` attr on `<Orateur>` (fiche ID) | **None** — name-only matching |
| Content | `<Para>` with Orateur child | `<Para>` with Orateur child (same) |
| Archive format | `.taz` per session | `.zip` bulk (all sessions) |

**IMPORTANT:** The Senat XML format is NOT Akoma Ntoso. It is DILA's own `PublicationDSenat` format (XSD at `schemas_Debats/publications/pub_DSenat_V01.xsd`). The reference to "Akoma Ntoso" in the ROADMAP was a planning assumption that turned out incorrect.

**Senat speaker matching:** No `href` with actor ID. Must match by normalized name against `actors` table (chamber='Senat'). Cross-reference lookup via `cross_references` where `source_type='senat_matricule'` is not viable for CRI (no matricule in XML). Pure name-based matching.

**DILA Senat .taz files for recent years:** The DILA `echanges.dila.gouv.fr/OPENDATA/Debats/SENAT/` directories for 2020-2026 are EMPTY. Only 2011-2016 have .taz files there. The canonical source for recent sessions is `data.senat.fr/data/debats/cri.zip`.

---

## Architecture Patterns

### Existing Pipeline Architecture (to preserve)

```
packages/ingestion/scripts/
├── config.py             # DB URL, API constants, rate limits
├── db.py                 # psycopg connection, upsert_query helper
├── utils.py              # download_zip_json_files, rate_limit, listify, fetch_json
├── ingest_debates.py     # EXISTING — needs refactoring (deputy → actor)
├── tag_interventions.py  # EXISTING — no changes needed
├── tags_dictionary.py    # EXISTING — no changes needed
└── run_all.py            # EXISTING — add new script steps
```

**New file to create:**
```
└── ingest_debates_senat.py   # NEW — Senat CRI from cri.zip
```

### Pattern 1: AN CRI Refactoring (ingest_debates.py)

**What needs changing:**
1. `INTERVENTION_COLUMNS`: rename `"deputy_id"` → `"actor_id"`
2. `load_deputy_cache()`: query `FROM actors WHERE chamber = 'AN'` (not `FROM deputies`)
3. `extract_an_id_from_href()`: the href fiche ID maps to `actors.official_id` (PA prefix stripped). Need to verify: AN actor official_ids stored as `PA795746` or just `795746`.
4. `build_intervention_records()`: rename `deputy_id` → `actor_id` in returned dict
5. `insert_interventions()`: the `chamber` column was added in migration 0001 — set it to `'AN'`
6. `upsert_debate()`: the `chamber` column exists in `debates` — set it to `'AN'`
7. `DEBATE_COLUMNS`: add `"chamber"` to the list (currently missing)
8. `build_debate_record()`: add `"chamber": "AN"` to returned dict

**AN actor official_id format:** Confirmed in Phase 10 — actors ingested from AMO10 with `official_id = uid` field (e.g., `PA795746`). The DILA href gives `795746`. So: `an_id = "PA" + extract_an_id_from_href(href)` to match `actors.official_id`.

### Pattern 2: Senat CRI Pipeline (ingest_debates_senat.py)

**Structure:** Mirror `ingest_debates.py` with Senat-specific parsing.

```python
DILA_SENAT_ZIP = "https://data.senat.fr/data/debats/cri.zip"
SENAT_XVIIe_START = datetime(2022, 6, 22)  # XVIIe legislature start

def download_cri_zip() -> dict[str, bytes]:
    """Download cri.zip and return {filename: xml_bytes} for all SEN_ files."""

def filter_xviie(files: dict) -> dict:
    """Keep only sessions from SENAT_XVIIe_START onwards by parsing filename date."""

def parse_senat_cri_xml(xml_bytes: bytes) -> dict | None:
    """Parse PublicationDSenat XML. Returns {metadata, interventions}."""
    # Root: PublicationDSenat
    # Date: root/Metadonnees/dateSeance
    # Session num: root/Metadonnees/numParution
    # Title: root/ContenuDSenat/CompteRendu/Contenu/PresidentSeance text
    # Interventions: all Para elements with Orateur/Nom child
    # Speaker name: Para/Orateur/Nom text (strip trailing punctuation)
    # Speaker role: Para/Orateur/Qualite text (if present)
    # Content: Para full text minus speaker name prefix
    # official_id: "SEN-{dateSeance}-{numParution}"

def load_senator_cache(conn) -> dict:
    """Load actors WHERE chamber='Senat' into {normalized_name: id}."""

def match_senator(name: str, by_name: dict) -> int | None:
    """Name-only matching: normalize and lookup."""
```

**official_id format for Senat debates:** `"SEN-{dateSeance}-{numSeance}"` — e.g., `"SEN-2024-01-15-001"`

### Pattern 3: Idempotency (both pipelines)

**Debates:** `ON CONFLICT (official_id) DO UPDATE SET ...` — already implemented via `upsert_query()` helper.

**Interventions:** Delete-then-insert per debate (already implemented in `insert_interventions()`). Pattern:
```python
DELETE FROM intervention_tags WHERE intervention_id IN (
    SELECT id FROM interventions WHERE debate_id = %s
)
DELETE FROM interventions WHERE debate_id = %s
INSERT INTO interventions ...
```
This is idempotent: re-running replaces all interventions for a debate.

### Pattern 4: cri.zip Memory Management

The cri.zip is 510 MB. Downloading entirely into memory on a 4GB RAM LXC is borderline. Use streaming or download to temp file:

```python
import tempfile, zipfile

def stream_senat_cri(start_date: datetime | None = None):
    """Stream cri.zip to temp file, yield (filename, xml_bytes) for XVIIe sessions."""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=True) as tmp:
        # Stream download to disk
        with httpx.stream('GET', DILA_SENAT_ZIP, timeout=300) as r:
            for chunk in r.iter_bytes(chunk_size=65536):
                tmp.write(chunk)
        tmp.flush()
        # Iterate zip members
        with zipfile.ZipFile(tmp.name) as zf:
            for name in zf.namelist():
                if not name.startswith('SEN_'):
                    continue
                date = parse_date_from_filename(name)  # SEN_YYYYMMDD_NNN.xml
                if start_date and date < start_date:
                    continue
                yield name, zf.read(name)
```

### Project Structure After Phase 11

```
packages/ingestion/scripts/
├── ingest_debates.py          # REFACTORED: deputy→actor, chamber='AN'
├── ingest_debates_senat.py    # NEW: Senat CRI from cri.zip
├── tag_interventions.py       # UNCHANGED
├── run_all.py                 # UPDATED: add steps 7b and 9
└── ...
```

**run_all.py steps after Phase 11:**
```
Step 7a: ingest_debates.py          (AN CRI)
Step 7b: ingest_debates_senat.py    (Senat CRI)  ← new
Step 8:  tag_interventions.py       (unchanged)
```

### Anti-Patterns to Avoid

- **Loading cri.zip into memory with httpx.get()**: 510 MB — use streaming download to temp file
- **Re-downloading cri.zip for every run**: add `--skip-senat-debates` and a `--senat-zip-path` option to use a locally cached file
- **Matching senators by official_id from href**: Senat XML has no href on Orateur — name-only
- **Using `deputies` table**: it was renamed to `actors` in migration 0001 — `FROM deputies` will fail

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML parsing | Custom regex | `lxml.etree` (already in requirements) | Handles encoding, namespaces, malformed XML |
| HTTP downloads | `urllib` | `httpx` (already in requirements) | Streaming, timeout, redirects |
| TAZ extraction | Custom decompressor | `tarfile` (stdlib) + `zcat` pattern | Already works for AN pipeline |
| ZIP extraction | Custom | `zipfile` (stdlib) | Works for cri.zip |
| DB upsert | Manual ON CONFLICT | `db.upsert_query()` (existing helper) | Consistent pattern across scripts |
| Rate limiting | `time.sleep()` inline | `utils.rate_limit()` (existing) | Centralized, configurable |
| Name normalization | Ad-hoc | Existing `normalize_name()` in ingest_debates.py | Already handles accents, punctuation |

**Key insight:** The existing AN pipeline is ~80% of what's needed for Senat. Copy-adapt rather than write from scratch.

---

## Common Pitfalls

### Pitfall 1: deputy_id vs actor_id column name
**What goes wrong:** `ingest_debates.py` still writes `deputy_id` in INTERVENTION_COLUMNS. The DB column is `actor_id` (renamed in migration 0001). INSERT fails.
**Why it happens:** Migration 0001 renamed the column, but the Python script was not updated.
**How to avoid:** In refactoring task, grep for `deputy_id` in `ingest_debates.py` and replace with `actor_id`. Also rename `load_deputy_cache` → `load_actor_cache` and update the query.
**Warning signs:** `psycopg.errors.UndefinedColumn: column "deputy_id" does not exist`

### Pitfall 2: AN official_id format mismatch in actor matching
**What goes wrong:** `extract_an_id_from_href()` returns `"795746"` (numeric string). Actors table has `official_id = "PA795746"`. No match found.
**Why it happens:** The href URL only contains the numeric ID; the PA prefix is added by the AN data ingestion.
**How to avoid:** Change the matching lookup: `by_official_id["PA" + an_id]` — prepend `"PA"` before lookup.
**Warning signs:** Zero deputy matches (100% unmatched) in AN ingestion stats after refactoring.

### Pitfall 3: Senat cri.zip memory exhaustion
**What goes wrong:** `httpx.get(DILA_SENAT_ZIP).content` loads 510 MB into RAM. On 4GB LXC, OOM kill.
**Why it happens:** `download_zip_json_files()` in utils.py uses `response.content` which buffers fully in memory. The existing helper works for small ZIPs (4.7MB AMO10) but not 510MB.
**How to avoid:** Use `httpx.stream()` + write to `tempfile.NamedTemporaryFile`. Do NOT reuse `download_zip_json_files()` from utils.py for this.
**Warning signs:** Process killed by OOM during download.

### Pitfall 4: debates.chamber column missing from DEBATE_COLUMNS
**What goes wrong:** `build_debate_record()` returns a dict with `"chamber": "AN"` but `DEBATE_COLUMNS` list doesn't include `"chamber"`. The `upsert_query()` helper generates SQL without the chamber column — chamber never gets set in DB.
**Why it happens:** `debates.chamber` was added in migration 0002 but the Python list was never updated.
**How to avoid:** Add `"chamber"` to `DEBATE_COLUMNS` in both AN and Senat scripts.
**Warning signs:** All debates have `chamber = 'AN'` (default) even after Senat ingestion, or chamber filter broken in frontend.

### Pitfall 5: Senat XML Orateur.Nom has trailing punctuation/space
**What goes wrong:** Speaker name parsed as `"M. François Marc."` instead of `"M. François Marc"`. Name matching fails.
**Why it happens:** The XML has `<Nom>M. François Marc.</Nom>` — trailing period is part of the element text.
**How to avoid:** Strip trailing `.,;: ` from `<Nom>` text, same as AN pipeline's `_parse_speaker()`.
**Warning signs:** Very low senator match rate despite senators being in DB.

### Pitfall 6: Senat dateSeance timezone offset
**What goes wrong:** `dateSeance = "2013-01-15+01:00"` — includes timezone offset. `datetime.strptime(date_str, "%Y-%m-%d")` fails.
**Why it happens:** Senat XML dates include timezone offset, AN XML does not.
**How to avoid:** Strip the timezone suffix before parsing: `date_str.split('+')[0].split('-')[0:3]` or use `dateutil.parser.parse()`.
**Warning signs:** `ValueError: unconverted data remains: +01:00` during date parsing.

### Pitfall 7: Tagging existing interventions vs new only
**What goes wrong:** `tag_interventions.py --retag-all` re-tags all 2479 existing interventions plus new ones. Without `--retag-all`, it only tags untagged interventions (WHERE NOT IN intervention_tags). If old interventions already have tags, the default mode is correct and efficient.
**Why it happens:** The script has two modes — the default (untagged only) is correct for incremental runs.
**How to avoid:** Default behavior is correct. Only pass `--retag-all` if the tag dictionary changes. Document this in run_all.py.

---

## Code Examples

### Refactored AN actor cache loading
```python
# Source: ingest_debates.py (refactored)
def load_actor_cache(conn) -> tuple[dict, dict]:
    """Load AN actors from DB into lookup dicts.
    Returns (by_official_id, by_name)
      by_official_id: {"PA795746": db_id}  -- key has PA prefix
      by_name: {normalized_full_name: db_id}
    """
    cur = conn.execute(
        "SELECT id, official_id, full_name FROM actors WHERE chamber = 'AN'"
    )
    by_official_id = {}
    by_name = {}
    for db_id, official_id, full_name in cur.fetchall():
        by_official_id[str(official_id)] = db_id  # "PA795746" key
        if full_name:
            name_str = full_name.decode() if isinstance(full_name, (bytes, memoryview)) else str(full_name)
            by_name[normalize_name(name_str)] = db_id
    return by_official_id, by_name
```

### AN href matching with PA prefix
```python
# Source: ingest_debates.py (refactored)
def match_actor_an(speaker_name, href, by_official_id, by_name):
    an_id = extract_an_id_from_href(href)
    if an_id:
        pa_id = "PA" + an_id  # prepend PA prefix
        if pa_id in by_official_id:
            return by_official_id[pa_id]
    # Fallback: name match
    clean = re.sub(r"^(M\.|Mme\.?|Mme|M)\s+", "", speaker_name).strip()
    return by_name.get(normalize_name(clean))
```

### Senat XML parsing (key elements)
```python
# Source: ingest_debates_senat.py (new)
def parse_senat_cri_xml(xml_bytes: bytes) -> dict | None:
    root = etree.fromstring(xml_bytes)

    # Metadata from root level
    meta = root.find("Metadonnees")
    date_str = _text(meta, "dateSeance")  # "2024-01-15+01:00"
    # Strip timezone offset
    if date_str:
        date_str = date_str.split("+")[0].split("-")  # handle both +HH and -HH tz
        # Better: use a simple split
        date_clean = re.sub(r"[+-]\d{2}:\d{2}$", "", _text(meta, "dateSeance") or "")

    num_parution = _text(meta, "numParution")
    session_nom = _text(meta.find("session"), "sessionOrd") if meta.find("session") else None

    # Presiding officer from PresidentSeance
    contenu = root.find(".//ContenuDSenat/CompteRendu/Contenu")
    pres_el = contenu.find("PresidentSeance") if contenu else None
    pres_text = pres_el.text.strip() if pres_el is not None and pres_el.text else None

    # official_id: "SEN-{date}-{num}"
    official_id = f"SEN-{date_clean}-{num_parution:0>3}"

    # Interventions: Para elements with Orateur/Nom child
    interventions = []
    for para in root.iter("Para"):
        orateur = para.find("Orateur")
        if orateur is None:
            continue
        nom_el = orateur.find("Nom")
        if nom_el is None or not nom_el.text:
            continue
        speaker_name = nom_el.text.strip().rstrip(".,;: ")
        qualite_el = orateur.find("Qualite")
        speaker_role = qualite_el.text.strip().rstrip(".,;: ") if qualite_el is not None and qualite_el.text else ""
        full_text = etree.tostring(para, method="text", encoding="unicode").strip()
        content = _extract_speech_content(full_text, nom_el.text.strip())
        if not content or len(content) < 5:
            continue
        interventions.append({
            "speaker_name": speaker_name,
            "speaker_role": speaker_role,
            "content": content,
        })
    return {"metadata": {...}, "interventions": interventions}
```

### Streaming cri.zip download
```python
# Source: ingest_debates_senat.py (new)
import tempfile, zipfile, re
from datetime import datetime

def download_cri_zip_to_temp() -> str:
    """Download cri.zip to a temp file. Returns temp file path."""
    url = "https://data.senat.fr/data/debats/cri.zip"
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes(chunk_size=65536):
            tmp.write(chunk)
    tmp.close()
    return tmp.name

def iter_xviie_sessions(zip_path: str, start_date: datetime):
    """Yield (filename, xml_bytes) for XVIIe sessions in the zip."""
    date_re = re.compile(r"SEN_(\d{4})(\d{2})(\d{2})_\d+\.xml")
    with zipfile.ZipFile(zip_path) as zf:
        for name in sorted(zf.namelist()):
            m = date_re.match(name)
            if not m:
                continue
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if d >= start_date:
                yield name, zf.read(name)
```

---

## Schema Compatibility

The existing `debates` + `interventions` tables fully support Phase 11 requirements:

| Column | Present | Default | Phase 11 usage |
|--------|---------|---------|----------------|
| `debates.chamber` | YES (migration 0002) | `'AN'` | Set to `'AN'` or `'Senat'` |
| `debates.official_id` | YES | — | `"AN-{parution}"` or `"SEN-{date}-{num}"` |
| `interventions.actor_id` | YES (renamed migration 0001) | NULL | Matched actor id or NULL |
| `interventions.chamber` | YES (migration 0001) | `'AN'` | Set to `'AN'` or `'Senat'` |
| `intervention_tags` | YES | — | Populated by tag_interventions.py |

**No new migrations needed for Phase 11.** Schema is complete.

---

## Thematic Tagging (INGEST-08)

The existing `tag_interventions.py` + `tags_dictionary.py` already handles both chambers correctly:

- Fetches interventions by `WHERE id NOT IN (SELECT intervention_id FROM intervention_tags)` — automatically picks up new interventions regardless of chamber
- The 12-tag dictionary covers: economie, securite, sante, education, environnement, justice, immigration, logement, transport, agriculture, numerique, culture
- **No changes needed** to tag_interventions.py or tags_dictionary.py for Phase 11

The only consideration: after initial AN re-ingestion (existing debates get delete+re-insert of interventions), old intervention IDs change → old tags become orphaned. This is handled correctly because `insert_interventions()` already deletes from `intervention_tags` before deleting interventions.

---

## run_all.py Update

Add two new steps and flags:

```python
# New steps to add to run_all.py
("Step 7a: ingest_debates.py (AN)",   not args.skip_debates),
("Step 7b: ingest_debates_senat.py",  not args.skip_senat_debates),  # new flag
("Step 8:  tag_interventions.py",     not args.skip_tags),

# New arg
parser.add_argument("--skip-senat-debates", action="store_true")
parser.add_argument("--senat-zip-path", type=str, default=None,
                    help="Path to pre-downloaded cri.zip (skip download)")
```

---

## Open Questions

1. **XVIIe legislature start date for Senat**
   - What we know: XVIIe legislature for AN started 2022-06-22 (elections). For the Senat, the renouvellement partial was September 2023. The Senat is a permanent body — "XVIIe legislature" for Senat = sessions concurrent with XVIIe AN legislature = from 2022-06-22.
   - What's unclear: Should we filter Senat sessions from 2022-06-22 (same as AN) or from the Senat's partial renewal date?
   - Recommendation: Use 2022-06-22 to match AN scope. Adjust to 2023-09-01 if success criteria require strict XVIIe Senat renewal. Given ~200 sessions expected, 2022-06-22 is the safe choice.

2. **Senat actor match rate**
   - What we know: Senat XML has no href on Orateur. Matching is name-only. Senators' names in XML may not exactly match `actors.full_name` (different civility prefixes, accents).
   - What's unclear: Expected match rate before knowing the actual name formats.
   - Recommendation: Log unmatched names to a file (not just counter) for post-run analysis. Use the same `normalize_name()` function from `ingest_debates.py`.

3. **Senat cri.zip re-download on every run**
   - What we know: 510 MB download takes ~2-5 minutes. Scheduled runs would re-download daily.
   - Recommendation: Add `--senat-zip-path` option to accept a pre-downloaded path. systemd timer can download separately or the script caches to `/tmp/cri_latest.zip` and checks Last-Modified header.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `packages/ingestion/scripts/ingest_debates.py` — full script read
- Direct inspection of `packages/shared/drizzle/` — all 5 migration files read
- Direct inspection of `packages/shared/src/schema.ts` — current schema
- `echanges.dila.gouv.fr/OPENDATA/Debats/SENAT/2013/SEN_20130116_001.taz` — downloaded and XML inspected via WSL
- `https://echanges.dila.gouv.fr/OPENDATA/Debats/SENAT/` — directory listing confirmed (2020-2026 empty)
- `curl -sI https://data.senat.fr/data/debats/cri.zip` — confirmed 510MB, last-modified 2026-03-30
- `packages/ingestion/scripts/run_all.py` — current orchestrator read

### Secondary (MEDIUM confidence)
- `data.gouv.fr/datasets/comptes-rendus-du-senat` — confirmed download URLs (cri.zip, debats.zip)
- `data.senat.fr/la-base-comptes-rendus/` — confirmed download URLs and coverage since 2003
- `echanges.dila.gouv.fr/OPENDATA/Debats/SENAT/2013/` — confirmed .taz file format + SEN_YYYYMMDD_NNN naming

### Tertiary (LOW confidence)
- XVIIe legislature start date for Senat filter — inferred from general knowledge, not verified from official source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing Python scripts read directly, no new dependencies needed
- Architecture: HIGH — refactoring scope identified precisely from code + schema inspection
- Senat XML format: HIGH — verified by downloading and parsing actual .taz file from DILA
- Senat data source URL: HIGH — verified HTTP HEAD confirming live file at cri.zip
- Pitfalls: HIGH — all pitfalls identified from direct code + schema inspection (concrete column/table names)
- Senat actor match rate: LOW — name-only matching, actual match rate unknown until run

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable — DILA AN format hasn't changed in years; cri.zip URL stable since 2013)
