# Phase 12: Ingestion Votes & Scrutins — Research

**Researched:** 2026-03-31
**Domain:** Python data ingestion — AN Scrutins.json.zip, Senat Dosleg PostgreSQL dump, votes/scrutins tables
**Confidence:** HIGH for AN pipeline (data source verified live), MEDIUM for Senat pipeline (Dosleg schema not directly inspected)

---

## Summary

Phase 12 ingests public parliamentary votes (scrutins) for both chambers into the `scrutins` + `votes` tables already created in Phase 9. The AN pipeline is simpler and higher confidence: a live ZIP at a known URL (19 MB, updated daily) containing per-scrutin JSON files. The Senat pipeline is more complex: the source is the Dosleg PostgreSQL 8.4 dump (~15 MB from `data.senat.fr/data/dosleg/dosleg.zip`), which requires schema inspection before any mapping can happen — this was flagged as a risk in STATE.md.

**Two distinct challenges:**

**Pipeline AN (12-01):** Download `Scrutins.json.zip`, parse individual JSON scrutin files, map to `scrutins` + `votes` tables. Actor matching uses `acteurRef` (PA-prefixed IDs) against `cross_references` where `source_type = 'PA'`. This is the same `PA*` ID system already established by `ingest_actors_an.py`. Volume: ~500+ scrutins, each with 577 individual vote records. **Fully plannable now.**

**Pipeline Senat (12-02):** Download `dosleg.zip`, restore into a temporary PostgreSQL instance or directly `pg_restore`/`psql` the SQL dump, inspect schema, then map Dosleg's scrutin tables to Poliscope's schema. The PG 8.4 dump compatibility with PG 17 is an explicit risk noted in STATE.md — must be handled first. Actor matching for senators uses their matricule (`official_id` in actors table, also in `cross_references` with `source_type = 'senat'` from Phase 10). **Needs schema discovery step first.**

**Primary recommendation:** Plan 12-01 (AN) first — it's immediately actionable and delivers the majority of value (~500 scrutins). Plan 12-02 (Senat) must start with a schema discovery task before mapping can be designed.

---

## Data Sources (Verified)

### Assemblee Nationale — Scrutins.json.zip

**URL:** `https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip`
- **Status:** HTTP 200, Content-Type: application/zip
- **Size:** 19.3 MB (updated daily — Last-Modified: 2026-03-31)
- **Content:** Per-scrutin JSON files, one file per scrutin

**JSON Structure (per Tricoteuses schema + nosdeputes.fr PR analysis):**
```json
{
  "scrutin": {
    "uid": "VTANR5L17V4785",
    "numero": "4785",
    "titre": "...",
    "dateScrutin": "2026-03-15",
    "typeVote": {
      "codeTypeVote": "SPS",
      "libelleTypeVote": "Scrutin public sur l'ensemble"
    },
    "sort": {
      "code": "adopté",
      "libelle": "Adopté"
    },
    "syntheseVote": {
      "nombreVotants": "524",
      "suffragesExprimes": "503",
      "nbrSuffragesRequis": "252",
      "pour": { "libelle": "Pour", "nbrVoix": "289" },
      "contre": { "libelle": "Contre", "nbrVoix": "214" },
      "abstentions": { "libelle": "Abstentions", "nbrVoix": "21" }
    },
    "ventilationVotes": {
      "organe": {
        "groupes": {
          "groupe": [
            {
              "organeRef": "PO...",
              "vote": {
                "decompteVoix": {
                  "pour": "50",
                  "contre": "0",
                  "abstentions": "2"
                },
                "decompteNominatif": {
                  "pours": { "votant": [ {"acteurRef": "PA841657", "mandatRef": "...", "parDelegation": "false"} ] },
                  "contres": { "votant": [...] },
                  "abstentions": { "votant": [...] },
                  "nonVotants": { "votant": [...] }
                }
              }
            }
          ]
        }
      }
    }
  }
}
```

**Key fields for mapping:**
- `scrutin.uid` → `scrutins.official_id` (e.g., `VTANR5L17V4785`)
- `scrutin.titre` → `scrutins.title`
- `scrutin.dateScrutin` → `scrutins.date`
- `scrutin.sort.code` → `scrutins.result` (map to `adopted`/`rejected`)
- `scrutin.typeVote.codeTypeVote` → `scrutins.scrutin_type`
- `scrutin.syntheseVote.pour.nbrVoix` → `scrutins.votes_for`
- Individual `votant.acteurRef` → lookup in `cross_references` where `source_type = 'PA'`
- Position in `pours`/`contres`/`abstentions`/`nonVotants` → `votes.position` (map to `for`/`against`/`abstain`/`absent`)

**Idempotency:** ON CONFLICT on `scrutins.official_id`; votes must DELETE + INSERT per scrutin (no unique constraint on `votes` — same pattern as interventions in Phase 11).

### Senat — Dosleg PostgreSQL Dump

**URL:** `https://data.senat.fr/data/dosleg/dosleg.zip`
- **Status:** HTTP 200, Content-Type: application/zip
- **Size:** 15.6 MB (updated daily — Last-Modified: 2026-03-31)
- **Format:** PostgreSQL 8.4 SQL dump (plain text or custom — must inspect)

**Known about Dosleg (from official docs + STATE.md):**
- Records all public votes since October 1, 2006
- Each scrutin includes: text voted on, result, analysis by political group, detailed position per senator
- PG 8.4 dump syntax may be incompatible with PG 17 (known risk — must test)

**Schema status:** NOT YET INSPECTED. The Dosleg database schema for scrutin/vote tables is unknown. The first task of 12-02 must be to download, restore (or directly parse as SQL text), and inspect the actual table structure.

**Actor matching for Senat:** Senators in `actors` table have `official_id` = matricule (e.g., `15019A`). Phase 10 populated `cross_references` with `source_type = 'senat'`. Dosleg likely references senators by matricule — needs verification during schema discovery.

---

## Standard Stack

### Core (same as existing ingestion scripts)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg | 3.x | PostgreSQL connection | Already used in all ingestion scripts |
| httpx | 0.x | HTTP downloads with streaming | Already in project, stream for large ZIPs |
| tqdm | 4.x | Progress bars | Already in project |
| python-dotenv | 1.x | .env loading via config.py | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| zipfile | stdlib | Extract ZIP archives | For both AN and Senat ZIPs |
| json | stdlib | Parse JSON files from AN ZIP | AN pipeline only |
| subprocess | stdlib | Run psql for Dosleg import | Senat schema discovery |
| tempfile | stdlib | Temp files for large downloads | Already pattern from cri.zip ingestion |

**Installation:** No new dependencies needed — all required libraries already present.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psql for Dosleg restore | pg_restore | Dosleg dump may be plain SQL, not custom format — psql is safer default |
| Direct SQL parse | Docker container restore | Docker adds infra complexity; plain `psql` into temp DB is simpler |

---

## Architecture Patterns

### Recommended Project Structure
```
packages/ingestion/scripts/
├── ingest_scrutins_an.py       # AN votes pipeline (12-01)
├── ingest_votes_senat.py       # Senat votes pipeline (12-02)
├── config.py                   # Add: AN_SCRUTINS_ZIP, SENAT_DOSLEG_ZIP constants
├── db.py                       # No changes needed
└── utils.py                    # No changes needed (download_zip_json_files reusable)
```

### Pattern 1: AN Scrutins Ingestion

**What:** Download ZIP → iterate JSON files → map fields → upsert scrutin → delete+insert votes
**When to use:** Idempotent batch ingestion of self-contained per-scrutin JSON files

```python
# Pattern: iterate files from ZIP, one scrutin per file
import io, json, zipfile
import httpx

def iter_scrutin_files(zip_url: str) -> Generator[dict, None, None]:
    """Stream ZIP to temp, yield parsed JSON for each scrutin file."""
    # Use streaming download (19 MB — small enough for httpx.get but streaming is safer)
    tmp_path = download_to_temp(zip_url)
    with zipfile.ZipFile(tmp_path) as zf:
        for name in zf.namelist():
            if name.endswith('.json'):
                with zf.open(name) as f:
                    data = json.load(f)
                    if 'scrutin' in data:
                        yield data['scrutin']

# Pattern: actor lookup via cross_references
def load_actor_cache_an(conn) -> dict[str, int]:
    """Load {PA_id: actor_db_id} from cross_references where source_type='PA'."""
    cur = conn.execute(
        "SELECT actor_id, source_id FROM cross_references WHERE source_type = 'PA'"
    )
    return {row[1]: row[0] for row in cur.fetchall()}

# Pattern: extract all individual votes from ventilationVotes
def extract_votes(scrutin: dict) -> list[tuple[str, str, bool]]:
    """Yield (acteurRef, position, par_delegation) from all voting groups."""
    # Navigate: ventilationVotes.organe.groupes.groupe (list or single)
    groupes = scrutin['ventilationVotes']['organe']['groupes']['groupe']
    if isinstance(groupes, dict):
        groupes = [groupes]
    for groupe in groupes:
        decompte = groupe['vote']['decompteNominatif']
        for position_key, position_val in [('pours', 'for'), ('contres', 'against'),
                                            ('abstentions', 'abstain'), ('nonVotants', 'absent')]:
            section = decompte.get(position_key, {})
            if not section:
                continue
            votants = section.get('votant', [])
            if isinstance(votants, dict):
                votants = [votants]
            for v in votants:
                yield v['acteurRef'], position_val, v.get('parDelegation') == 'true'

# Pattern: upsert scrutin + delete/insert votes (idempotent)
def upsert_scrutin_and_votes(conn, scrutin_data: dict, votes: list[dict]) -> int:
    """Upsert scrutin row, delete+insert votes. Returns votes inserted count."""
    query = upsert_query('scrutins', SCRUTIN_COLUMNS, 'official_id') + ' RETURNING id'
    row = conn.execute(query, scrutin_data).fetchone()
    scrutin_id = row[0]
    # Delete existing votes for this scrutin (idempotent)
    conn.execute('DELETE FROM votes WHERE scrutin_id = %s', (scrutin_id,))
    # Bulk insert votes
    for vote in votes:
        vote['scrutin_id'] = scrutin_id
        conn.execute(INSERT_VOTE_QUERY, vote)
    conn.commit()
    return len(votes)
```

### Pattern 2: Senat Dosleg Schema Discovery (first task of 12-02)

**What:** Download dosleg.zip, restore into a throwaway local DB, inspect tables
**When to use:** Unknown third-party schema — must inspect before coding

```bash
# Step 1: Download and inspect dump format
curl -o /tmp/dosleg.zip https://data.senat.fr/data/dosleg/dosleg.zip
cd /tmp && unzip dosleg.zip

# Step 2: Check if plain SQL or custom format
file dosleg.sql  # or whatever the extracted file is named
head -50 dosleg.sql  # Check PG version header and syntax

# Step 3: Test PG17 compatibility
# Plain SQL dumps from PG 8.4 often use old syntax that works fine in PG 17
# Known issues: old-style OWNER TO, GRANT statements with old syntax
# If psql import fails: check error line, fix syntax, re-import

# Step 4: Inspect scrutin-related tables
psql -U poliscope -d poliscope_dosleg_test -c "\dt" | grep -i scrutin
psql -U poliscope -d poliscope_dosleg_test -c "\d scrutin_table_name"
psql -U poliscope -d poliscope_dosleg_test -c "SELECT * FROM scrutin_table LIMIT 3;"
```

### Pattern 3: Position Value Mapping

The `votes.position` column uses English values (`for`/`against`/`abstain`/`absent`) per schema.

```python
# AN JSON uses section names, Senat Dosleg uses unknown (to verify)
AN_POSITION_MAP = {
    'pours': 'for',
    'contres': 'against',
    'abstentions': 'abstain',
    'nonVotants': 'absent',
}

# nosdeputes API (not used directly, reference only) uses:
# 'pour', 'contre', 'nonVotant' — different from section keys above
```

### Pattern 4: scrutin.official_id Format

**AN:** `VTANR5L17V{numero}` — e.g., `VTANR5L17V4785`  
Note: the `uid` in the JSON may be this form. Verify by inspecting first file.

**Senat:** Unknown until schema inspection. Likely a numeric ID or `SEN-YYYY-NNN` style — TBD in 12-02.

### Anti-Patterns to Avoid

- **Loading entire ZIP into RAM:** 19 MB is manageable but use `download_to_temp()` pattern for consistency with cri.zip approach
- **Accessing `groupe` as list without listify():** The `ventilationVotes.organe.groupes.groupe` is a list when multiple groups exist but a single dict when only one — always listify
- **Accessing `votant` as list without listify():** Same issue — a single votant becomes a dict, not a list; always listify
- **Skipping `nonVotants`:** NonVotants must be stored as `absent` — they are deputies present but not voting (members of government, session chair, etc.)
- **Restoring Dosleg into production DB:** Always restore to a throwaway/temp DB for inspection; do NOT import Dosleg schema into the Poliscope production DB

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON ZIP iteration | Custom ZIP parser | `zipfile` stdlib | Already works, proven in utils.py |
| Actor ID lookup | In-script dict building | `cross_references` table + PA source_type | Already populated by Phase 10 |
| Upsert logic | Custom ON CONFLICT logic | `db.upsert_query()` helper | Already in db.py, tested |
| HTTP download | requests/urllib | `httpx` (already in project) | Consistent with other scripts |
| Vote deduplication | Custom tracking | DELETE+INSERT per scrutin | Same idempotency pattern as interventions |

**Key insight:** The actor matching system (cross_references table + `source_type = 'PA'`) is already designed exactly for this use case. For AN: load `{source_id: actor_id}` where `source_type = 'PA'`, then look up `acteurRef` directly — no name matching needed, unlike the Senat CRI debates.

---

## Common Pitfalls

### Pitfall 1: ventilationVotes Group/Votant as Dict Not List
**What goes wrong:** `json['ventilationVotes']['organe']['groupes']['groupe']` returns a `dict` (not `list`) when only one parliamentary group voted. Iterating it gives key names, not group objects.
**Why it happens:** The AN XML-to-JSON conversion doesn't enforce array types for single-element collections.
**How to avoid:** Always `listify()` (the existing helper in utils.py) before iterating groups and votants.
**Warning signs:** Script processes 0 votes for scrutins with small vote counts.

### Pitfall 2: Missing `nonVotants` Section
**What goes wrong:** Some scrutins have no `nonVotants` key in `decompteNominatif` — accessing it raises KeyError.
**Why it happens:** If no deputy is in the nonVotant category, the key may be absent.
**How to avoid:** Use `.get('nonVotants', {})` and check for None before iterating.

### Pitfall 3: Dosleg PG 8.4 Dump Syntax Issues
**What goes wrong:** `psql` on PG 17 fails on old syntax like `ENCODING = 'SQL_ASCII'`, old `ALTER TABLE ... OWNER TO`, or tablespace references.
**Why it happens:** PG 8.4 dump uses syntax deprecated or removed by PG 17.
**How to avoid:** Inspect dump with `head -100`, fix specific syntax issues before import. Common fixes: remove `ENCODING` clause, remove tablespace clauses. Test on throwaway DB first.
**Warning signs:** psql exits with error on first CREATE DATABASE statement.

### Pitfall 4: parDelegation Is a String "true"/"false", Not a Boolean
**What goes wrong:** Checking `if v['parDelegation']` always evaluates to True (non-empty string).
**Why it happens:** JSON from AN open data stores boolean fields as string values.
**How to avoid:** Always compare `v.get('parDelegation') == 'true'`.

### Pitfall 5: Actor Unmatched = Silent Data Loss
**What goes wrong:** Votes from deputies who left mid-legislature (or ministers) have `acteurRef` not in `cross_references`. Silently skipping them drops votes from the database.
**Why it happens:** `cross_references` only contains currently active deputies (ingested in Phase 10).
**How to avoid:** Log unmatched `acteurRef` values. The decision to skip or insert NULL actorId (rejected by FK constraint) must be made explicitly. **Recommendation: skip unmatched votes but log count and IDs** — same decision made in Phase 11 for Senat interventions.

### Pitfall 6: session_id FK (scrutins → debates)
**What goes wrong:** `scrutins.session_id` is a FK to `debates.id`. AN scrutin JSON contains `seanceRef` which references a session, but the mapping from `seanceRef` to a debates row may not exist (sessions may not be in DB if they pre-date Phase 11 ingestion scope).
**Why it happens:** Not all sessions are in the debates table — only XVIIe legislature sessions from Phase 11.
**How to avoid:** Set `session_id = NULL` if the session lookup fails. The FK allows NULL, so this is safe.

---

## Code Examples

Verified patterns from existing codebase:

### Cross-Reference Actor Lookup (verified pattern from ingest_actors_an.py)
```python
# Source: packages/ingestion/scripts/ingest_actors_an.py
# For AN: source_type='PA', source_id=official_id (e.g., 'PA841657')
conn.execute(
    "SELECT id, official_id FROM actors WHERE chamber='AN' AND official_id = ANY(%s)",
    (official_ids,),
)
# For votes: use cross_references table directly
conn.execute(
    "SELECT actor_id, source_id FROM cross_references WHERE source_type = 'PA'"
)
```

### Streaming Download to Temp File (verified pattern from ingest_debates_senat.py)
```python
# Source: packages/ingestion/scripts/ingest_debates_senat.py
import tempfile, httpx, os

def download_to_temp(url: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes(chunk_size=65536):
                tmp.write(chunk)
        tmp.close()
        return tmp.name
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise
```

### Upsert Query Builder (verified from db.py)
```python
# Source: packages/ingestion/scripts/db.py
from db import upsert_query
query = upsert_query(
    table="scrutins",
    columns=SCRUTIN_COLUMNS,
    conflict_column="official_id",
) + " RETURNING id"
```

### listify Helper (verified from utils.py)
```python
# Source: packages/ingestion/scripts/utils.py
from utils import listify
# Critical: groupe and votant are dict (not list) when single element
groupes = listify(ventilation['organe']['groupes']['groupe'])
for groupe in groupes:
    votants = listify(groupe['vote']['decompteNominatif']['pours'].get('votant'))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| nosdeputes.fr API for votes | Direct AN open data Scrutins.json.zip | Phase 10+ | No rate limiting, no dependency on third party |
| Senat scraping | Dosleg PostgreSQL dump | Phase 12 | Structured data, covers all votes since 2006 |
| actor matching by name | cross_references table by PA ID | Phase 10 | 100% reliable matching for AN; name fallback only needed for Senat |

**Deprecated/outdated:**
- nosdeputes.fr API (`/16/scrutin/N/json`): still works for 16th legislature but not a primary source for Poliscope — use official AN open data instead
- PG 8.4 Dosleg dump format: still the only official Senat source as of 2026-03-31; no modern JSON/CSV alternative for individual senator vote positions

---

## Open Questions

1. **Dosleg exact schema for scrutin/vote tables**
   - What we know: Dosleg records all public votes since 2006; format is PG 8.4 SQL dump; size is ~15 MB
   - What's unclear: table names, column names, how senator IDs are stored, whether they match `official_id` or `cross_references.source_id`
   - Recommendation: First task of 12-02 must be a schema discovery step — download dump, try to restore into a temp PG DB, inspect with `\d` and sample rows

2. **AN scrutin `uid` vs `numero` field naming**
   - What we know: PR analysis shows both `uid` and `numero` exist; `uid` appears to be `VTANR5L17V{numero}`
   - What's unclear: exact field name in the XVIIe ZIP (format may have changed from previous legislatures)
   - Recommendation: Inspect first file from the ZIP at the start of 12-01 implementation

3. **Senat vote coverage via Dosleg**
   - What we know: Dosleg records votes since 2006, but the dump is for legislative work (Dosleg = "dossiers législatifs")
   - What's unclear: whether Dosleg contains individual senator vote positions or only aggregate results
   - Recommendation: Inspect during schema discovery; if Dosleg lacks individual positions, fallback to scraping `senat.fr/scrutin-public/YYYY/scrYYYY-N.html` pages (HTML parsing, more complex)

4. **`nonVotants` and `causePositionVote` field**
   - What we know: Tricoteuses schema has `causePositionVote` with values MG/PAN/PSE for government members/session chair
   - What's unclear: whether these should be stored differently from absent deputies
   - Recommendation: Store all as `absent` position; ignore `causePositionVote` for v1 — can add column later if needed

---

## Sources

### Primary (HIGH confidence)
- Direct HTTP HEAD to `https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json.zip` — confirmed live, 19 MB, updated daily
- Direct HTTP HEAD to `https://data.senat.fr/data/dosleg/dosleg.zip` — confirmed live, 15.6 MB, updated daily
- `packages/shared/src/schema.ts` — scrutins + votes table schema (read directly)
- `packages/shared/drizzle/0002_add-universal-schema.sql` — confirmed scrutins/votes tables with all indexes
- `packages/ingestion/scripts/ingest_actors_an.py` — cross_references pattern with `source_type='PA'`
- `packages/ingestion/scripts/db.py` — upsert_query() helper
- `packages/ingestion/scripts/utils.py` — listify(), download_zip_json_files(), streaming pattern
- `packages/ingestion/scripts/ingest_debates_senat.py` — streaming download temp file pattern

### Secondary (MEDIUM confidence)
- Tricoteuses/tricoteuses-assemblee `Votant.json` schema — confirms `acteurRef`, `mandatRef`, `parDelegation` fields
- nosdeputes.fr PR #115 — confirms `syntheseVote`, `ventilationVotes`, `decompteNominatif` structure with pours/contres/abstentions/nonVotants sections
- data.senat.fr/aide/travaux-legislatifs-base-dosleg/ — confirms Dosleg records all votes since 2006 with per-senator detail
- nosdeputes.fr API scrutin endpoint (`/16/scrutin/1/json`) — confirmed `pour`/`contre`/`nonVotant` position values and `par_delegation` field

### Tertiary (LOW confidence)
- Dosleg table schema — NOT inspected; assumed to contain scrutin + vote_senateur tables based on official description

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — same stack as Phases 10/11, no new dependencies
- AN architecture: HIGH — data source verified live, JSON structure confirmed via multiple sources
- Senat architecture: MEDIUM — Dosleg existence confirmed, but schema unknown until inspected
- Pitfalls: HIGH — listify pitfall is a known pattern from Phase 10/11; PG 8.4 is a flagged known risk
- Actor matching: HIGH — cross_references table is designed exactly for this, PA source_type already populated

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (data source URLs stable; Dosleg schema discovery needed before Senat pipeline design)
