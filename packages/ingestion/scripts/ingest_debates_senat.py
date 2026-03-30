"""Ingest Senat debates and interventions from data.senat.fr CRI bulk ZIP.

Source: https://data.senat.fr/data/debats/cri.zip
Format: ZIP archive containing per-session XML files (PublicationDSenat format, NOT Akoma Ntoso).

The ZIP is ~510 MB and is streamed to a temp file to avoid OOM on the 4GB LXC.
Only sessions from the XVIIe legislature (>= 2022-06-22) are ingested.
Senator matching is name-only (no href/ID on Orateur in Senat XML).
"""

import argparse
import logging
import os
import re
import tempfile
import unicodedata
import zipfile
from datetime import datetime

import httpx
from lxml import etree
from tqdm import tqdm

from config import DATABASE_URL  # noqa: F401 — triggers .env load
from db import get_connection, upsert_query
from ingest_debates import _clean_unicode, _extract_speech_content, normalize_name

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DILA_SENAT_ZIP = "https://data.senat.fr/data/debats/cri.zip"
XVIIE_START = datetime(2022, 6, 22)

DEBATE_COLUMNS = [
    "official_id",
    "title",
    "date",
    "legislature",
    "session_type",
    "presiding_officer",
    "source_url",
    "chamber",
]

INTERVENTION_COLUMNS = [
    "debate_id",
    "actor_id",
    "speaker_name",
    "speaker_role",
    "content",
    "order_in_debate",
    "chamber",
]

# Filename pattern: SEN_YYYYMMDD_NNN.xml
_FILENAME_RE = re.compile(r"SEN_(\d{4})(\d{2})(\d{2})_(\d+)\.xml")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_cri_zip_to_temp() -> str:
    """Stream cri.zip to a temp file on disk. Returns temp file path.

    Uses httpx.stream to avoid loading 510 MB into RAM on the 4GB LXC.
    """
    logger.info("Downloading cri.zip from %s (streaming to temp file)...", DILA_SENAT_ZIP)
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with httpx.stream("GET", DILA_SENAT_ZIP, timeout=600, follow_redirects=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            for chunk in r.iter_bytes(chunk_size=65536):
                tmp.write(chunk)
                downloaded += len(chunk)
        tmp.close()
        logger.info("Downloaded %.1f MB to %s", downloaded / 1e6, tmp.name)
        return tmp.name
    except Exception:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# ZIP iteration
# ---------------------------------------------------------------------------

def iter_xviie_sessions(zip_path: str, start_date: datetime):
    """Yield (filename, xml_bytes) for sessions on or after start_date.

    Filters by filename date pattern SEN_YYYYMMDD_NNN.xml.
    Skips entries that do not match the expected filename pattern.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
        logger.info("ZIP contains %d entries", len(names))
        for name in names:
            # Strip directory prefix if present
            basename = name.rsplit("/", 1)[-1]
            m = _FILENAME_RE.match(basename)
            if not m:
                continue
            try:
                session_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
            if session_date < start_date:
                continue
            try:
                xml_bytes = zf.read(name)
            except Exception as e:
                logger.warning("Could not read %s from zip: %s", name, e)
                continue
            yield name, xml_bytes


# ---------------------------------------------------------------------------
# Helper: text extraction
# ---------------------------------------------------------------------------

def _text(element, tag: str) -> str | None:
    """Return stripped text of a child element, or None."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _strip_tz(date_str: str) -> str:
    """Strip timezone offset from date string like '2024-01-15+01:00' or '2024-01-15-01:00'.

    The Senat XML includes a timezone suffix after the date; strptime cannot parse it.
    We strip everything after the date portion (YYYY-MM-DD).
    """
    return re.sub(r"[+-]\d{2}:\d{2}$", "", date_str).strip()


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def parse_senat_cri_xml(xml_bytes: bytes) -> dict | None:
    """Parse a PublicationDSenat XML file.

    Returns {metadata: {...}, interventions: [...]} or None on failure.
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        logger.error("XML parse error: %s", e)
        return None

    # Metadata at root level
    meta = root.find("Metadonnees")
    if meta is None:
        logger.warning("No Metadonnees element in PublicationDSenat")
        return None

    # Date: "2024-01-15+01:00" — strip timezone offset
    date_str_raw = _text(meta, "dateSeance")
    if not date_str_raw:
        logger.warning("No dateSeance in Metadonnees")
        return None

    date_clean = _strip_tz(date_str_raw)
    try:
        session_date = datetime.strptime(date_clean, "%Y-%m-%d")
    except ValueError as e:
        logger.warning("Could not parse date '%s': %s", date_clean, e)
        return None

    num_parution = _text(meta, "numParution") or "1"
    num_seance = _text(meta, "numSeance")

    # Session type from session/sessionOrd
    session_el = meta.find("session")
    session_type = None
    if session_el is not None:
        session_type = _text(session_el, "sessionOrd")

    # official_id: SEN-YYYY-MM-DD-NNN (zero-padded to 3 digits)
    try:
        num_int = int(num_parution)
    except (ValueError, TypeError):
        num_int = 1
    official_id = f"SEN-{date_clean}-{num_int:03d}"

    # Navigate to content
    contenu = root.find(".//ContenuDSenat/CompteRendu/Contenu")

    # Presiding officer from PresidentSeance text
    presiding_officer = None
    if contenu is not None:
        pres_el = contenu.find("PresidentSeance")
        if pres_el is not None and pres_el.text:
            presiding_officer = pres_el.text.strip().rstrip(".,;: ")

    # Title: use presiding officer context or fallback
    title = f"Seance du {date_clean}"

    # Interventions: iterate all Para elements with Orateur/Nom child
    interventions = []
    search_root = contenu if contenu is not None else root
    for para in search_root.iter("Para"):
        orateur = para.find("Orateur")
        if orateur is None:
            continue
        nom_el = orateur.find("Nom")
        if nom_el is None or not nom_el.text:
            continue

        speaker_name_raw = nom_el.text.strip()
        # Strip trailing punctuation that Senat XML adds to names
        speaker_name = speaker_name_raw.rstrip(".,;: ")
        if not speaker_name:
            continue

        # Role from Orateur/Qualite (not QualiteMouvement as in AN)
        qualite_el = orateur.find("Qualite")
        speaker_role = ""
        if qualite_el is not None and qualite_el.text:
            speaker_role = qualite_el.text.strip().rstrip(".,;: ")

        # Full text content of the Para element
        full_text = etree.tostring(para, method="text", encoding="unicode").strip()

        # Extract speech content (remove speaker name prefix)
        content = _clean_unicode(_extract_speech_content(full_text, speaker_name_raw))
        if not content or len(content) < 5:
            continue

        interventions.append({
            "speaker_name": speaker_name,
            "speaker_role": speaker_role,
            "content": content,
        })

    metadata = {
        "official_id": official_id,
        "date": session_date,
        "date_clean": date_clean,
        "num_parution": num_parution,
        "num_seance": num_seance,
        "session_type": session_type or "hemicycle",
        "title": title,
        "presiding_officer": presiding_officer,
    }

    return {"metadata": metadata, "interventions": interventions}


# ---------------------------------------------------------------------------
# Senator cache + matching
# ---------------------------------------------------------------------------

def load_senator_cache(conn) -> dict[str, int]:
    """Load Senat actors from DB into a normalized-name lookup dict.

    Returns {normalized_full_name: db_id} for all actors WHERE chamber = 'Senat'.
    """
    cur = conn.execute(
        "SELECT id, official_id, full_name FROM actors WHERE chamber = 'Senat'"
    )
    rows = cur.fetchall()

    by_name: dict[str, int] = {}
    for db_id, _official_id, full_name in rows:
        if full_name:
            name_str = (
                full_name.decode("utf-8")
                if isinstance(full_name, (bytes, memoryview))
                else str(full_name)
            )
            by_name[normalize_name(name_str)] = db_id

    logger.info("Senator cache loaded: %d actors by name", len(by_name))
    return by_name


def match_senator(
    speaker_name: str,
    by_name: dict[str, int],
    unmatched_log: list[str] | None = None,
) -> int | None:
    """Match a speaker name to a senator in the DB (name-only matching).

    Strips civility prefixes (M., Mme, etc.) before normalizing.
    Logs unmatched names if unmatched_log list is provided.
    """
    # Strip civility prefix
    clean = re.sub(r"^(M\.\s*|Mme\.?\s*|M\s+)", "", speaker_name).strip()
    normalized = normalize_name(clean)
    result = by_name.get(normalized)
    if result is None and unmatched_log is not None:
        unmatched_log.append(speaker_name)
    return result


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def upsert_debate(conn, debate_data: dict) -> int:
    """Insert or update a Senat debate, return its DB id."""
    query = upsert_query(
        table="debates",
        columns=DEBATE_COLUMNS,
        conflict_column="official_id",
        has_updated_at=False,
    )
    query += " RETURNING id"
    cur = conn.execute(query, debate_data)
    row = cur.fetchone()
    return row[0]


def insert_interventions(conn, debate_id: int, interventions: list[dict]) -> int:
    """Delete existing interventions for debate, insert fresh batch. Idempotent.

    Returns number of interventions inserted.
    """
    # Delete tags first (FK constraint), then interventions
    conn.execute(
        "DELETE FROM intervention_tags WHERE intervention_id IN "
        "(SELECT id FROM interventions WHERE debate_id = %s)",
        (debate_id,),
    )
    conn.execute("DELETE FROM interventions WHERE debate_id = %s", (debate_id,))

    if not interventions:
        return 0

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

def build_intervention_records(
    raw_interventions: list[dict],
    by_name: dict[str, int],
    unmatched_log: list[str] | None = None,
) -> tuple[list[dict], int, int]:
    """Build intervention dicts from parsed Senat CRI data.

    Returns (records, matched_count, unmatched_count).
    """
    records = []
    matched = 0
    unmatched = 0

    for idx, raw in enumerate(raw_interventions, start=1):
        actor_id = match_senator(raw["speaker_name"], by_name, unmatched_log)

        if actor_id is not None:
            matched += 1
        else:
            unmatched += 1

        records.append({
            "actor_id": actor_id,
            "speaker_name": raw["speaker_name"],
            "speaker_role": raw.get("speaker_role", ""),
            "content": raw["content"],
            "order_in_debate": idx,
            "chamber": "Senat",
        })

    return records, matched, unmatched


def ingest_debates_senat(
    limit: int | None = None,
    start_date: datetime | None = None,
    dry_run: bool = False,
    senat_zip_path: str | None = None,
    log_unmatched: bool = False,
) -> dict:
    """Main ingestion entry point for Senat CRI.

    Parameters
    ----------
    limit : int, optional
        Max number of sessions to process.
    start_date : datetime, optional
        Only ingest sessions on or after this date. Default: XVIIe legislature start.
    dry_run : bool
        Parse without writing to DB.
    senat_zip_path : str, optional
        Path to a pre-downloaded cri.zip (skips download).
    log_unmatched : bool
        Write unmatched speaker names to senat_unmatched_speakers.log.

    Returns
    -------
    dict with stats
    """
    if start_date is None:
        start_date = XVIIE_START

    stats = {
        "debates_processed": 0,
        "interventions_inserted": 0,
        "actor_matches": 0,
        "actor_unmatched": 0,
        "errors": 0,
        "skipped_date": 0,
    }

    unmatched_names: list[str] = []
    temp_path_to_cleanup: str | None = None

    try:
        # Download or use local zip
        if senat_zip_path:
            logger.info("Using local cri.zip: %s", senat_zip_path)
            zip_path = senat_zip_path
        else:
            zip_path = download_cri_zip_to_temp()
            temp_path_to_cleanup = zip_path

        # Collect sessions to process
        logger.info("Iterating sessions from XVIIe start (%s)...", start_date.date())
        sessions = list(iter_xviie_sessions(zip_path, start_date))
        logger.info("Found %d sessions for XVIIe legislature", len(sessions))

        if limit:
            sessions = sessions[:limit]
            logger.info("Limited to %d sessions", limit)

        if not sessions:
            logger.warning("No sessions found matching criteria")
            return stats

        # Connect to DB (or prepare dry-run mode)
        conn = None
        by_name: dict[str, int] = {}
        if not dry_run:
            conn = get_connection()
            by_name = load_senator_cache(conn)
        else:
            logger.info("DRY-RUN mode — no DB writes")
            try:
                conn_tmp = get_connection()
                by_name = load_senator_cache(conn_tmp)
                conn_tmp.close()
            except Exception:
                logger.info("Could not load senator cache in dry-run (DB not available)")

        for filename, xml_bytes in tqdm(sessions, desc="Ingesting Senat debates", unit="session"):
            try:
                parsed = parse_senat_cri_xml(xml_bytes)
                if parsed is None:
                    stats["errors"] += 1
                    logger.warning("Failed to parse %s", filename)
                    continue

                metadata = parsed["metadata"]
                raw_interventions = parsed["interventions"]

                # Build debate record
                debate_data = {
                    "official_id": metadata["official_id"],
                    "title": metadata["title"],
                    "date": metadata["date"],
                    "legislature": 17,
                    "session_type": metadata["session_type"],
                    "presiding_officer": metadata["presiding_officer"],
                    "source_url": DILA_SENAT_ZIP,
                    "chamber": "Senat",
                }

                # Build intervention records
                records, matched, unmatched = build_intervention_records(
                    raw_interventions,
                    by_name,
                    unmatched_log=unmatched_names if log_unmatched else None,
                )

                if dry_run:
                    logger.info(
                        "[DRY-RUN] Would upsert debate: %s (%s) with %d interventions (%d matched, %d unmatched)",
                        debate_data["official_id"],
                        debate_data["date"].date(),
                        len(records),
                        matched,
                        unmatched,
                    )
                    stats["debates_processed"] += 1
                    stats["interventions_inserted"] += len(records)
                    stats["actor_matches"] += matched
                    stats["actor_unmatched"] += unmatched
                    continue

                # Upsert debate + interventions in a transaction
                debate_id = upsert_debate(conn, debate_data)
                inserted = insert_interventions(conn, debate_id, records)
                conn.commit()

                stats["debates_processed"] += 1
                stats["interventions_inserted"] += inserted
                stats["actor_matches"] += matched
                stats["actor_unmatched"] += unmatched

            except Exception as e:
                logger.error("Error processing %s: %s", filename, e, exc_info=True)
                stats["errors"] += 1
                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

    finally:
        if conn is not None:
            conn.close()
        if temp_path_to_cleanup:
            try:
                os.unlink(temp_path_to_cleanup)
                logger.info("Cleaned up temp file: %s", temp_path_to_cleanup)
            except OSError:
                pass

    # Write unmatched names to log file
    if log_unmatched and unmatched_names:
        log_path = os.path.join(os.path.dirname(__file__), "senat_unmatched_speakers.log")
        unique_names = sorted(set(unmatched_names))
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(unique_names) + "\n")
        logger.info("Wrote %d unique unmatched speaker names to %s", len(unique_names), log_path)

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingest Senat CRI debates and interventions from data.senat.fr cri.zip.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of sessions to process (default: all)",
    )
    parser.add_argument(
        "--start-date", type=str, default=None,
        help="Start date filter YYYY-MM-DD (default: 2022-06-22, XVIIe legislature)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse without writing to DB",
    )
    parser.add_argument(
        "--senat-zip-path", type=str, default=None,
        help="Path to pre-downloaded cri.zip (skips download)",
    )
    parser.add_argument(
        "--log-unmatched", action="store_true",
        help="Write unmatched speaker names to senat_unmatched_speakers.log",
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )

    start_date = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError as e:
            logger.error("Invalid --start-date: %s", e)
            raise SystemExit(1)

    stats = ingest_debates_senat(
        limit=args.limit,
        start_date=start_date,
        dry_run=args.dry_run,
        senat_zip_path=args.senat_zip_path,
        log_unmatched=args.log_unmatched,
    )

    logger.info("=" * 60)
    logger.info("SENAT INGESTION COMPLETE")
    logger.info("  Debates processed:       %d", stats["debates_processed"])
    logger.info("  Interventions inserted:  %d", stats["interventions_inserted"])
    logger.info("  Actor matches:           %d", stats["actor_matches"])
    logger.info("  Actor unmatched:         %d", stats["actor_unmatched"])
    logger.info("  Errors:                  %d", stats["errors"])
    logger.info("  Skipped (date filter):   %d", stats["skipped_date"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
