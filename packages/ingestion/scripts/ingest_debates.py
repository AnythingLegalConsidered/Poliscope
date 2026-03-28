"""Ingest debates and interventions from DILA open data (Assemblee Nationale).

Source: https://echanges.dila.gouv.fr/OPENDATA/Debats/AN/
Format: .taz archives containing CRI (Compte Rendu Integral) XML files.

Fallback from nosdeputes.fr /seances/json which returns empty data for the
17th legislature as of 2026-03.
"""

import argparse
import io
import json
import logging
import re
import tarfile
import unicodedata
from datetime import datetime

import httpx
from lxml import etree
from tqdm import tqdm

from config import DATABASE_URL, NOSDEPUTES_BASE, REQUEST_DELAY
from db import get_connection, upsert_query
from utils import fetch_json, rate_limit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DILA_BASE = "https://echanges.dila.gouv.fr/OPENDATA/Debats/AN"
LEGISLATURE = 17

DEBATE_COLUMNS = [
    "official_id",
    "title",
    "date",
    "legislature",
    "session_type",
    "presiding_officer",
    "source_url",
]

INTERVENTION_COLUMNS = [
    "debate_id",
    "deputy_id",
    "speaker_name",
    "speaker_role",
    "content",
    "order_in_debate",
]


# ---------------------------------------------------------------------------
# Deputy cache
# ---------------------------------------------------------------------------

def load_deputy_cache(conn) -> tuple[dict, dict]:
    """Load deputies from DB into lookup dicts.

    Returns
    -------
    (by_official_id, by_name)
        by_official_id: {official_id: db_id}
        by_name: {normalized_full_name: db_id}
    """
    cur = conn.execute("SELECT id, official_id, full_name FROM deputies")
    rows = cur.fetchall()

    by_official_id: dict[str, int] = {}
    by_name: dict[str, int] = {}

    for db_id, official_id, full_name in rows:
        by_official_id[str(official_id)] = db_id
        if full_name:
            name_str = full_name.decode("utf-8") if isinstance(full_name, (bytes, memoryview)) else str(full_name)
            by_name[normalize_name(name_str)] = db_id

    logger.info("Deputy cache loaded: %d by official_id, %d by name", len(by_official_id), len(by_name))
    return by_official_id, by_name


def normalize_name(name: str) -> str:
    """Normalize a name for fuzzy matching: lowercase, strip accents, strip punctuation."""
    name = name.lower().strip()
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Remove punctuation except spaces and hyphens
    name = re.sub(r"[^\w\s-]", "", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


# ---------------------------------------------------------------------------
# DILA file listing
# ---------------------------------------------------------------------------

def list_taz_files(years: list[int]) -> list[dict]:
    """List all .taz files from DILA for given years.

    Returns list of {filename, url, year, parution}.
    """
    all_files = []
    client = httpx.Client(timeout=30, follow_redirects=True)

    for year in years:
        url = f"{DILA_BASE}/{year}/"
        try:
            r = client.get(url)
            r.raise_for_status()
            # Parse directory listing for .taz links
            filenames = re.findall(r'href="(AN_\d+\.taz)"', r.text)
            for fname in filenames:
                # Extract parution number from filename: AN_2025001.taz -> 2025001
                match = re.match(r"AN_(\d+)\.taz", fname)
                parution = match.group(1) if match else fname
                all_files.append({
                    "filename": fname,
                    "url": f"{DILA_BASE}/{year}/{fname}",
                    "year": year,
                    "parution": parution,
                })
            logger.info("Found %d .taz files for year %d", len(filenames), year)
        except httpx.HTTPError as e:
            logger.warning("Failed to list files for year %d: %s", year, e)

    client.close()
    return sorted(all_files, key=lambda f: f["parution"])


# ---------------------------------------------------------------------------
# TAZ download + XML extraction
# ---------------------------------------------------------------------------

def download_and_extract_cri(url: str) -> bytes | None:
    """Download a .taz file and extract the CRI XML content.

    The .taz format is a tar containing a .tar, which contains CRI_*.xml and AAA_*.xml.
    We only want CRI_*.xml (Compte Rendu Integral).
    """
    client = httpx.Client(timeout=60, follow_redirects=True)
    try:
        r = client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Failed to download %s: %s", url, e)
        return None
    finally:
        client.close()

    try:
        # Outer tar
        outer = tarfile.open(fileobj=io.BytesIO(r.content))
        inner_name = outer.getnames()[0]
        inner_data = outer.extractfile(inner_name).read()
        outer.close()

        # Inner tar
        inner = tarfile.open(fileobj=io.BytesIO(inner_data))
        for member_name in inner.getnames():
            if member_name.startswith("CRI_") and member_name.endswith(".xml"):
                xml_bytes = inner.extractfile(member_name).read()
                inner.close()
                return xml_bytes
        inner.close()
        logger.warning("No CRI XML found in %s", url)
        return None
    except (tarfile.TarError, Exception) as e:
        logger.error("Failed to extract CRI from %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def parse_cri_xml(xml_bytes: bytes) -> dict | None:
    """Parse a CRI XML file into a structured dict.

    Returns {metadata: {...}, interventions: [{speaker_name, speaker_role, content, href}, ...]}
    or None on parse failure.
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        logger.error("XML parse error: %s", e)
        return None

    # Extract metadata from CompteRendu/Metadonnees
    cr = root.find(".//CompteRendu")
    if cr is None:
        logger.warning("No CompteRendu element found in XML")
        return None

    meta_el = cr.find("Metadonnees")
    metadata = {}
    if meta_el is not None:
        metadata = {
            "parution": _text(meta_el, "parution"),
            "date_seance": _text(meta_el, "dateSeance"),
            "num_seance": _text(meta_el, "numSeance"),
            "num_seance_jour": _text(meta_el, "numSeanceJour"),
            "type_assemblee": _text(meta_el, "typeAssemblee"),
            "validite": _text(meta_el, "validite"),
        }

    # Extract legislature from top-level Metadonnees
    top_meta = root.find("Metadonnees")
    if top_meta is not None:
        metadata["legislature"] = _text(top_meta, "LegislatureNumero")
        metadata["session_nom"] = _text(top_meta, "SessionNom")
        metadata["date_parution"] = _text(top_meta, "DateParution")

    # Extract session title from Quantiemes
    quantiemes = cr.find(".//Quantiemes")
    if quantiemes is not None:
        metadata["journee"] = _text(quantiemes, "Journee")

    # Extract interventions: each <Para> with an <Orateur> child is an intervention
    interventions = []
    contenu = cr.find("Contenu")
    if contenu is None:
        return {"metadata": metadata, "interventions": []}

    for para in contenu.iter("Para"):
        orateur = para.find("Orateur")
        if orateur is None:
            continue

        nom_el = orateur.find("Nom")
        speaker_name_raw = nom_el.text.strip() if nom_el is not None and nom_el.text else ""
        if not speaker_name_raw:
            continue

        href = orateur.get("href", "")

        # Get full text content (strip XML tags)
        full_text = etree.tostring(para, method="text", encoding="unicode").strip()

        # Remove the speaker name prefix from the text
        # The text usually starts with "M. Speaker Name. Content..."
        # We want just the content after the speaker name
        content = _clean_unicode(_extract_speech_content(full_text, speaker_name_raw))

        # Skip empty interventions (procedural notes, etc.)
        if not content or len(content) < 5:
            continue

        # Parse speaker name and role
        speaker_name, speaker_role = _parse_speaker(speaker_name_raw, para)

        interventions.append({
            "speaker_name": speaker_name,
            "speaker_role": speaker_role,
            "content": content,
            "href": href,
        })

    return {"metadata": metadata, "interventions": interventions}


def _text(element, tag: str) -> str | None:
    """Get text content of a child element, or None."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _extract_speech_content(full_text: str, speaker_name_raw: str) -> str:
    """Extract speech content by removing the speaker name prefix."""
    # The full text starts with something like "M. Bayrou,Premier ministre... Content"
    # Find the first period after speaker identification and take from there
    # Try to find where the actual speech starts (after ". " following speaker info)

    # Simple approach: remove the raw speaker name from the beginning
    text = full_text.strip()

    # Remove leading speaker name (with variations)
    # Speaker name raw might be "M. François Bayrou," or "Mme la présidente."
    if speaker_name_raw and text.startswith(speaker_name_raw):
        text = text[len(speaker_name_raw):].strip()

    # If there's a QualiteMouvement (role) prefix, it comes right after the name
    # e.g. "Premier ministre, chargé de..." followed by ". " then content
    # Look for the pattern: role text followed by ". " which starts the speech
    # But sometimes the role IS part of the content introduction

    # Clean up leading punctuation
    text = text.lstrip(".,;: ")

    # Remove stage directions at the start (parenthesized content)
    text = re.sub(r"^\([^)]*\)\s*", "", text)

    return text.strip()


def _clean_unicode(text: str) -> str:
    """Replace problematic Unicode chars with safe equivalents."""
    replacements = {
        '\u00a0': ' ',      # non-breaking space → space
        '\u2019': "'",      # right single quote → apostrophe
        '\u2018': "'",      # left single quote → apostrophe
        '\u201c': '"',      # left double quote
        '\u201d': '"',      # right double quote
        '\u2013': '-',      # en dash
        '\u2014': ' - ',    # em dash
        '\ufffd': '',       # replacement character → remove
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _parse_speaker(speaker_name_raw: str, para_element) -> tuple[str, str]:
    """Parse speaker name and role from raw name and QualiteMouvement elements.

    Returns (clean_name, role).
    """
    # Clean the raw speaker name: remove trailing punctuation
    name = speaker_name_raw.rstrip(".,;: ")

    # Check for role in QualiteMouvement child of Para
    role = ""
    qm = para_element.find("QualiteMouvement")
    if qm is not None and qm.text:
        qm_text = qm.text.strip()
        # QualiteMouvement can be a role like "Premier ministre" or a stage direction
        # Stage directions are in parentheses
        if not qm_text.startswith("("):
            role = qm_text.rstrip(".,;: ")

    # Detect roles from the name itself
    name_lower = name.lower()
    if "président" in name_lower or "présidente" in name_lower:
        if not role:
            role = "président"
    elif "ministre" in name_lower:
        if not role:
            role = "ministre"
    elif "secrétaire d'état" in name_lower or "secrétaire d'état" in name_lower:
        if not role:
            role = "secrétaire d'état"

    # Remove group abbreviation from name: "M. Boris Vallaud (SOC)" -> "M. Boris Vallaud"
    name = re.sub(r"\s*\([A-Z-]+\)\s*$", "", name)

    return name, role


# ---------------------------------------------------------------------------
# Deputy matching
# ---------------------------------------------------------------------------

def extract_an_id_from_href(href: str) -> str | None:
    """Extract AN fiche ID from DILA href URL.

    Example: http://www.assemblee-nationale.fr/17/tribun/fiches_id/795746.asp -> 795746
    """
    if not href:
        return None
    match = re.search(r"/fiches_id/(\d+)\.asp", href)
    return match.group(1) if match else None


def match_deputy(
    speaker_name: str,
    href: str,
    by_official_id: dict[str, int],
    by_name: dict[str, int],
) -> int | None:
    """Try to match a speaker to a deputy in the DB.

    Strategy:
    1. Extract AN ID from href -> match by official_id
    2. Fallback: normalize speaker name -> match by name
    """
    # Strategy 1: Match by AN fiche ID
    an_id = extract_an_id_from_href(href)
    if an_id and an_id in by_official_id:
        return by_official_id[an_id]

    # Strategy 2: Match by normalized name
    # Clean the speaker name: remove "M.", "Mme", "Mme.", etc.
    clean = re.sub(r"^(M\.|Mme\.?|Mme|M)\s+", "", speaker_name).strip()
    normalized = normalize_name(clean)
    if normalized in by_name:
        return by_name[normalized]

    return None


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def upsert_debate(conn, debate_data: dict) -> int:
    """Insert or update a debate, return its DB id."""
    query = upsert_query(
        table="debates",
        columns=DEBATE_COLUMNS,
        conflict_column="official_id",
        has_updated_at=False,
    )
    # Add RETURNING id to get the DB id
    query += " RETURNING id"
    cur = conn.execute(query, debate_data)
    row = cur.fetchone()
    return row[0]


def insert_interventions(conn, debate_id: int, interventions: list[dict]) -> int:
    """Delete existing interventions for debate, insert fresh batch.

    Returns number of interventions inserted.
    """
    # Idempotence: delete tags then interventions for this debate
    conn.execute(
        "DELETE FROM intervention_tags WHERE intervention_id IN "
        "(SELECT id FROM interventions WHERE debate_id = %s)",
        (debate_id,),
    )
    conn.execute("DELETE FROM interventions WHERE debate_id = %s", (debate_id,))

    if not interventions:
        return 0

    # Build batch insert (no upsert needed since we just deleted)
    cols = INTERVENTION_COLUMNS
    col_list = ", ".join(cols)
    placeholders = ", ".join(f"%({c})s" for c in cols)
    query = f"INSERT INTO interventions ({col_list}) VALUES ({placeholders})"

    count = 0
    for intervention in interventions:
        intervention["debate_id"] = debate_id
        conn.execute(query, intervention)
        count += 1

    return count


# ---------------------------------------------------------------------------
# Main ingestion logic
# ---------------------------------------------------------------------------

def extract_presiding_officer(raw_interventions: list[dict]) -> str | None:
    """Return the name of the first speaker with a président/présidente role."""
    for intervention in raw_interventions:
        role = (intervention.get("speaker_role") or "").lower()
        if "président" in role or "présidente" in role:
            return intervention["speaker_name"]
    return None


def build_debate_record(metadata: dict, parution: str) -> dict:
    """Build a debate dict from CRI metadata."""
    date_str = metadata.get("date_seance")
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            date = datetime.now()
    else:
        date = datetime.now()

    # Title: use Journee if available, else generate from date
    title = metadata.get("journee") or f"Seance du {date_str or 'inconnue'}"

    # Session type
    session_type = metadata.get("session_nom") or "hemicycle"

    # Source URL
    source_url = f"{DILA_BASE}/{date.year}/AN_{parution}.taz"

    legislature = int(metadata.get("legislature") or LEGISLATURE)

    return {
        "official_id": f"AN-{parution}",
        "title": title,
        "date": date,
        "legislature": legislature,
        "session_type": session_type,
        "presiding_officer": None,  # filled by caller
        "source_url": source_url,
    }


def build_intervention_records(
    raw_interventions: list[dict],
    by_official_id: dict[str, int],
    by_name: dict[str, int],
) -> tuple[list[dict], int, int]:
    """Build intervention dicts from parsed CRI data.

    Returns (records, matched_count, unmatched_count).
    """
    records = []
    matched = 0
    unmatched = 0

    for idx, raw in enumerate(raw_interventions, start=1):
        deputy_id = match_deputy(
            raw["speaker_name"],
            raw.get("href", ""),
            by_official_id,
            by_name,
        )

        if deputy_id:
            matched += 1
        else:
            unmatched += 1

        records.append({
            "deputy_id": deputy_id,
            "speaker_name": raw["speaker_name"],
            "speaker_role": raw.get("speaker_role", ""),
            "content": raw["content"],
            "order_in_debate": idx,
        })

    return records, matched, unmatched


def ingest_debates(
    years: list[int] | None = None,
    limit: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Main ingestion entry point.

    Parameters
    ----------
    years : list of int, optional
        Years to ingest. Default: [2024, 2025].
    limit : int, optional
        Max number of sessions to process.
    start_date, end_date : str, optional
        Filter by date range (YYYY-MM-DD).
    dry_run : bool
        If True, fetch and parse but do not write to DB.

    Returns
    -------
    dict with stats: debates_processed, interventions_inserted, errors, deputy_matches, deputy_unmatched
    """
    if years is None:
        years = [2024, 2025, 2026]

    stats = {
        "debates_processed": 0,
        "interventions_inserted": 0,
        "errors": 0,
        "deputy_matches": 0,
        "deputy_unmatched": 0,
        "skipped_date": 0,
    }

    # Parse date filters
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    # List available .taz files
    logger.info("Listing .taz files for years: %s", years)
    taz_files = list_taz_files(years)
    logger.info("Found %d .taz files total", len(taz_files))

    if limit:
        taz_files = taz_files[:limit]
        logger.info("Limited to %d files", limit)

    if not taz_files:
        logger.warning("No .taz files found")
        return stats

    # Load deputy cache (skip in dry-run if no DB needed, but we still need it for matching)
    if not dry_run:
        conn = get_connection()
        by_official_id, by_name = load_deputy_cache(conn)
    else:
        by_official_id, by_name = {}, {}
        # Try to load cache even in dry-run for matching info
        try:
            conn_tmp = get_connection()
            by_official_id, by_name = load_deputy_cache(conn_tmp)
            conn_tmp.close()
        except Exception:
            logger.info("Could not load deputy cache in dry-run mode (DB not available)")

    # Debug: log structure of first file
    first_logged = False

    for taz_info in tqdm(taz_files, desc="Ingesting debates", unit="session"):
        try:
            # Download and extract CRI XML
            xml_bytes = download_and_extract_cri(taz_info["url"])
            rate_limit()

            if xml_bytes is None:
                stats["errors"] += 1
                continue

            # Parse XML
            parsed = parse_cri_xml(xml_bytes)
            if parsed is None:
                stats["errors"] += 1
                continue

            metadata = parsed["metadata"]
            raw_interventions = parsed["interventions"]

            # Debug: log first response structure
            if not first_logged:
                logger.info(
                    "First CRI structure:\n%s",
                    json.dumps(metadata, indent=2, ensure_ascii=False, default=str),
                )
                logger.info(
                    "First CRI has %d interventions. Sample speakers: %s",
                    len(raw_interventions),
                    [i["speaker_name"] for i in raw_interventions[:5]],
                )
                first_logged = True

            # Date filtering
            date_str = metadata.get("date_seance")
            if date_str:
                try:
                    seance_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if start_dt and seance_date < start_dt:
                        stats["skipped_date"] += 1
                        continue
                    if end_dt and seance_date > end_dt:
                        stats["skipped_date"] += 1
                        continue
                except ValueError:
                    pass

            if dry_run:
                # In dry-run, just log what would be done
                debate_data = build_debate_record(metadata, taz_info["parution"])
                debate_data["presiding_officer"] = extract_presiding_officer(raw_interventions)
                records, matched, unmatched = build_intervention_records(
                    raw_interventions, by_official_id, by_name,
                )
                logger.info(
                    "[DRY-RUN] Would upsert debate: %s (%s) with %d interventions (%d matched, %d unmatched)",
                    debate_data["title"],
                    debate_data["date"],
                    len(records),
                    matched,
                    unmatched,
                )
                stats["debates_processed"] += 1
                stats["interventions_inserted"] += len(records)
                stats["deputy_matches"] += matched
                stats["deputy_unmatched"] += unmatched
                continue

            # Build debate record
            debate_data = build_debate_record(metadata, taz_info["parution"])
            debate_data["presiding_officer"] = extract_presiding_officer(raw_interventions)

            # Build intervention records
            records, matched, unmatched = build_intervention_records(
                raw_interventions, by_official_id, by_name,
            )

            # Upsert debate + interventions in a single transaction
            debate_id = upsert_debate(conn, debate_data)
            inserted = insert_interventions(conn, debate_id, records)
            conn.commit()

            stats["debates_processed"] += 1
            stats["interventions_inserted"] += inserted
            stats["deputy_matches"] += matched
            stats["deputy_unmatched"] += unmatched

        except Exception as e:
            logger.error("Error processing %s: %s", taz_info["filename"], e, exc_info=True)
            stats["errors"] += 1
            if not dry_run:
                try:
                    conn.rollback()
                except Exception:
                    pass

    if not dry_run:
        conn.close()

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingest AN debate sessions and interventions from DILA open data.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of sessions to process (default: all)",
    )
    parser.add_argument(
        "--start-date", type=str, default=None,
        help="Start date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date", type=str, default=None,
        help="End date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and parse without writing to DB",
    )
    parser.add_argument(
        "--years", type=int, nargs="+", default=None,
        help="Years to ingest (default: 2024 2025 2026)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )

    stats = ingest_debates(
        years=args.years,
        limit=args.limit,
        start_date=args.start_date,
        end_date=args.end_date,
        dry_run=args.dry_run,
    )

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("  Debates processed:       %d", stats["debates_processed"])
    logger.info("  Interventions inserted:   %d", stats["interventions_inserted"])
    logger.info("  Deputy matches:           %d", stats["deputy_matches"])
    logger.info("  Deputy unmatched:         %d", stats["deputy_unmatched"])
    logger.info("  Errors:                   %d", stats["errors"])
    logger.info("  Skipped (date filter):    %d", stats["skipped_date"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
