"""Ingest Senat debates and interventions from data.senat.fr CRI bulk ZIP.

Source: https://data.senat.fr/data/debats/cri.zip
Format: ZIP archive containing per-session XML files (cri:cri namespace,
        http://senat.fr/schemas/thb/cri). Filename format: cri/dYYYYMMDD.xml.

The ZIP is ~510 MB and is streamed to a temp file to avoid OOM on the 4GB LXC.
Only sessions from the XVIIe legislature (>= 2022-06-22) are ingested.
Senator matching uses the mat= attribute (official_id in actors table) first,
falling back to name normalization for speakers not in the DB (ministers, etc.).

Bug fixes vs original implementation:
  - Filename regex updated from SEN_YYYYMMDD_NNN.xml to dYYYYMMDD.xml
  - XML parser updated: lxml XMLParser(recover=True) handles malformed HTML/XML
    mixed documents (tag mismatches in older Senat CRI files)
  - XML elements: cri:intervenant with nom/civ/qua/mat attrs instead of
    PublicationDSenat Para/Orateur/Nom elements
  - Date sourced from filename (not XML metadata)
  - official_id derived from mat attribute for direct DB matching
  - UnboundLocalError in finally block fixed: conn initialized before try block
"""

import argparse
import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime

import httpx
from lxml import etree
from tqdm import tqdm

from config import DATABASE_URL  # noqa: F401 — triggers .env load
from db import get_connection, upsert_query
from ingest_debates import _clean_unicode, normalize_name

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DILA_SENAT_ZIP = "https://data.senat.fr/data/debats/cri.zip"
XVIIE_START = datetime(2022, 6, 22)
CRI_NS = "http://senat.fr/schemas/thb/cri"

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

# Filename pattern: cri/dYYYYMMDD.xml
_FILENAME_RE = re.compile(r"d(\d{4})(\d{2})(\d{2})\.xml")


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

    Filters by filename date pattern dYYYYMMDD.xml.
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
            yield name, session_date, xml_bytes


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def parse_senat_cri_xml(xml_bytes: bytes, session_date: datetime, filename: str) -> dict | None:
    """Parse a Senat CRI XML file (cri:cri namespace format).

    Returns {metadata: {...}, interventions: [...]} or None on failure.

    Uses XMLParser(recover=True) to handle tag-mismatch errors common in
    older Senat CRI files (mixed HTML/XML with unclosed div tags).
    """
    try:
        parser = etree.XMLParser(recover=True, encoding="iso-8859-1")
        root = etree.fromstring(xml_bytes, parser=parser)
    except Exception as e:
        logger.error("XML parse error for %s: %s", filename, e)
        return None

    # Date from filename (XML metadata is unreliable / absent in older files)
    date_clean = session_date.strftime("%Y-%m-%d")

    # official_id: SEN-YYYY-MM-DD (one file per date in this format)
    official_id = f"SEN-{date_clean}"

    # Presiding officer: first intervenant with qua="président de séance"
    presiding_officer = None
    intervs_all = root.findall(f".//{{{CRI_NS}}}intervenant")
    for iv in intervs_all:
        qua = iv.get("qua", "")
        if "président de séance" in qua.lower() or "president de seance" in qua.lower():
            nom = iv.get("nom", "").strip()
            if nom:
                presiding_officer = nom
                break

    title = f"Séance du {date_clean}"

    # Interventions: all cri:intervenant elements with nom and mat attributes
    interventions = []
    seen_interv_ids = set()  # deduplicate by intervenant id

    for iv in intervs_all:
        iv_id = iv.get("id", "")
        if iv_id and iv_id in seen_interv_ids:
            continue
        if iv_id:
            seen_interv_ids.add(iv_id)

        nom = iv.get("nom", "").strip()
        if not nom:
            continue

        mat = iv.get("mat", "").strip()  # senator matricule = official_id in actors
        civ = iv.get("civ", "").strip()
        qua = iv.get("qua", "").strip()

        # Build display name with civility
        speaker_name = f"{civ} {nom}".strip() if civ else nom

        # Full text content of the intervenant element
        full_text = etree.tostring(iv, method="text", encoding="unicode").strip()
        content = _clean_unicode(full_text) if full_text else ""
        if not content or len(content) < 5:
            continue

        interventions.append({
            "speaker_name": speaker_name,
            "speaker_name_raw": nom,  # used for fallback name matching
            "speaker_role": qua,
            "mat": mat,
            "content": content,
        })

    metadata = {
        "official_id": official_id,
        "date": session_date,
        "date_clean": date_clean,
        "session_type": "hemicycle",
        "title": title,
        "presiding_officer": presiding_officer,
    }

    return {"metadata": metadata, "interventions": interventions}


# ---------------------------------------------------------------------------
# Senator cache + matching
# ---------------------------------------------------------------------------

def load_senator_cache(conn) -> tuple[dict[str, int], dict[str, int]]:
    """Load Senat actors from DB into two lookup dicts.

    Returns:
        by_mat: {official_id: db_id}  — primary matching via mat attribute
        by_name: {normalized_full_name: db_id}  — fallback name matching
    """
    cur = conn.execute(
        "SELECT id, official_id, full_name FROM actors WHERE chamber = 'Senat'"
    )
    rows = cur.fetchall()

    by_mat: dict[str, int] = {}
    by_name: dict[str, int] = {}
    for db_id, official_id, full_name in rows:
        # Decode bytes if needed (psycopg3 binary protocol)
        oid_str = (
            official_id.decode("utf-8") if isinstance(official_id, (bytes, memoryview))
            else str(official_id)
        ) if official_id else ""
        name_str = (
            full_name.decode("utf-8") if isinstance(full_name, (bytes, memoryview))
            else str(full_name)
        ) if full_name else ""

        if oid_str:
            by_mat[oid_str] = db_id
        if name_str:
            by_name[normalize_name(name_str)] = db_id

    logger.info(
        "Senator cache loaded: %d by mat, %d by name",
        len(by_mat), len(by_name),
    )
    return by_mat, by_name


def match_senator(
    mat: str,
    speaker_name_raw: str,
    by_mat: dict[str, int],
    by_name: dict[str, int],
    unmatched_log: list[str] | None = None,
) -> int | None:
    """Match a speaker to a senator in the DB.

    Priority:
    1. mat attribute (official_id direct lookup) — most reliable
    2. Normalized full name fallback — for ministers/non-senator speakers
    """
    # Primary: mat-based lookup
    if mat and mat in by_mat:
        return by_mat[mat]

    # Fallback: name normalization
    clean = re.sub(r"^(M\.\s*|Mme\.?\s*|M\s+)", "", speaker_name_raw).strip()
    normalized = normalize_name(clean)
    result = by_name.get(normalized)
    if result is None and unmatched_log is not None:
        unmatched_log.append(speaker_name_raw)
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
    by_mat: dict[str, int],
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
        actor_id = match_senator(
            mat=raw.get("mat", ""),
            speaker_name_raw=raw.get("speaker_name_raw", raw["speaker_name"]),
            by_mat=by_mat,
            by_name=by_name,
            unmatched_log=unmatched_log,
        )

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
    # Initialize conn before try block to avoid UnboundLocalError in finally
    conn = None

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
        by_mat: dict[str, int] = {}
        by_name: dict[str, int] = {}
        if not dry_run:
            conn = get_connection()
            by_mat, by_name = load_senator_cache(conn)
        else:
            logger.info("DRY-RUN mode — no DB writes")
            try:
                conn_tmp = get_connection()
                by_mat, by_name = load_senator_cache(conn_tmp)
                conn_tmp.close()
            except Exception:
                logger.info("Could not load senator cache in dry-run (DB not available)")

        for filename, session_date, xml_bytes in tqdm(sessions, desc="Ingesting Senat debates", unit="session"):
            try:
                parsed = parse_senat_cri_xml(xml_bytes, session_date, filename)
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
                    by_mat,
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
