"""Ingest Senat scrutins (public votes) + individual senator vote positions into scrutins + votes tables.

Downloads dosleg.zip from data.senat.fr, parses the PostgreSQL SQL dump as plain text
to extract COPY blocks for `scr` (scrutins) and `votsen` (individual senator votes),
then maps them to Poliscope's scrutins + votes schema.

Actor matching uses `actors.official_id` WHERE `chamber = 'Senat'`.  Senator matricules
in Dosleg (character(6) with potential trailing space) are stripped before lookup.

Schema discovered from dosleg.zip (PG 8.4 plain SQL dump):
  scr(sesann, scrnum, code, scrint, scrdat, scrpou, scrcon, scrvot, scrsuf,
       scrvotsea, scrsufsea, scrpousea, scrconsea, scrmaj, scrmajsea, soslib,
       scrbaspag, scrdateff, scrjso)
  votsen(sesann, scrnum, senmat, posvotcod, titsencod, stavotidt, senmatdel, votsenmar)
  posvot codes: 1=pour, 2=contre, 3=abstention, 4=non-votant

Idempotency:
  - scrutins upserted by official_id (ON CONFLICT DO UPDATE)
  - votes: DELETE + INSERT per scrutin_id (same pattern as ingest_scrutins_an.py)

Scope filter: only scrutins with scrdat >= 2022-06-22 (XVIIe legislature start).

Usage:
    python ingest_scrutins_senat.py
    python ingest_scrutins_senat.py --dry-run   # Parse only, no DB writes
"""

import argparse
import io
import logging
import os
import tempfile
import zipfile
from datetime import date, datetime

import httpx
from tqdm import tqdm

from config import SENAT_DOSLEG_ZIP
from db import get_connection, upsert_query

logger = logging.getLogger(__name__)

# XVIIe legislature start date (same constant used in ingest_debates_senat.py)
XVIIE_START = date(2022, 6, 22)

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

SCRUTIN_COLUMNS = [
    "official_id",
    "title",
    "date",
    "chamber",
    "session_id",
    "legislature_id",
    "scrutin_type",
    "result",
    "votes_for",
    "votes_against",
    "votes_abstain",
    "source_url",
]

_INSERT_VOTE = (
    "INSERT INTO votes (scrutin_id, actor_id, position, delegation_actor_id) "
    "VALUES (%(scrutin_id)s, %(actor_id)s, %(position)s, %(delegation_actor_id)s)"
)

_UPSERT_SCRUTIN = upsert_query("scrutins", SCRUTIN_COLUMNS, "official_id")

# Dosleg posvotcod -> Poliscope position values
_POSITION_MAP: dict[str, str] = {
    "1": "for",
    "2": "against",
    "3": "abstain",
    "4": "absent",
}

# ---------------------------------------------------------------------------
# SQL dump parsing helpers
# ---------------------------------------------------------------------------


def _parse_copy_block(sql_text: str, table_name: str) -> list[list[str]]:
    """Extract COPY block rows for *table_name* from a plain-SQL PG dump.

    Handles both 'COPY table_name (' and 'COPY public.table_name (' headers.
    Returns a list of rows, each row is a list of raw column value strings
    (tab-separated, NULL represented as '\\N').
    """
    rows: list[list[str]] = []
    in_block = False

    for line in sql_text.splitlines():
        if not in_block:
            # Match either 'COPY table_name (' or 'COPY public.table_name ('
            stripped = line.strip()
            if stripped.startswith(f"COPY {table_name} (") or stripped.startswith(
                f"COPY public.{table_name} ("
            ):
                in_block = True
                continue
        else:
            # End of COPY block
            if line == "\\.":
                break
            rows.append(line.split("\t"))

    return rows


def _parse_date(value: str) -> date | None:
    """Parse 'YYYY-MM-DD HH:MM:SS' timestamp from Dosleg into a date object."""
    if not value or value == "\\N":
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------


def _download_dosleg_sql() -> str:
    """Download dosleg.zip and return the extracted SQL as a string.

    Uses streaming download to avoid OOM on large files.
    """
    logger.info("Downloading Dosleg dump: %s", SENAT_DOSLEG_ZIP)
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with httpx.stream("GET", SENAT_DOSLEG_ZIP, timeout=300, follow_redirects=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            for chunk in r.iter_bytes(chunk_size=65536):
                tmp.write(chunk)
                downloaded += len(chunk)
        tmp.close()
        logger.info("Download complete: %.1f MB", downloaded / 1_048_576)

        with zipfile.ZipFile(tmp.name) as zf:
            names = zf.namelist()
            sql_name = next((n for n in names if n.endswith(".sql")), None)
            if not sql_name:
                raise ValueError(f"No .sql file found in dosleg.zip, got: {names}")
            logger.info("Extracting %s (%.1f MB compressed)", sql_name, os.path.getsize(tmp.name) / 1_048_576)
            with zf.open(sql_name) as f:
                return f.read().decode("utf-8")
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Cache builder
# ---------------------------------------------------------------------------


def load_actor_cache_senat(conn) -> dict[str, int]:
    """Return {official_id: actor_id} for all Senat actors.

    Keys are senator matricules (e.g., '20054A'), values are DB integer actor ids.
    This is the direct-lookup path: Dosleg senmat matches actors.official_id exactly.
    """
    cur = conn.execute(
        "SELECT id, official_id FROM actors WHERE chamber = 'Senat'"
    )
    cache: dict[str, int] = {}
    for row in cur.fetchall():
        actor_id = row[0]
        official_id = row[1]
        # Decode bytes if needed (psycopg3 binary protocol)
        if isinstance(official_id, (bytes, memoryview)):
            official_id = bytes(official_id).decode("utf-8")
        cache[official_id.strip()] = actor_id
    logger.info("Loaded %d Senat actor references from actors table", len(cache))
    return cache


# ---------------------------------------------------------------------------
# Data parsers
# ---------------------------------------------------------------------------


def parse_scrutins(rows: list[list[str]]) -> dict[tuple[str, str], dict]:
    """Parse scr COPY rows into a dict keyed by (sesann, scrnum).

    Filters to scrutins with scrdat >= XVIIE_START.
    Returns:
        {(sesann, scrnum): scrutin_record_dict}
    """
    # scr column order (0-indexed):
    # 0:sesann 1:scrnum 2:code 3:scrint 4:scrdat 5:scrpou 6:scrcon
    # 7:scrvot 8:scrsuf 9:scrvotsea 10:scrsufsea 11:scrpousea 12:scrconsea
    # 13:scrmaj 14:scrmajsea 15:soslib 16:scrbaspag 17:scrdateff 18:scrjso

    result: dict[tuple[str, str], dict] = {}
    skipped_old = 0
    skipped_bad = 0

    for row in rows:
        if len(row) < 7:
            skipped_bad += 1
            continue

        sesann = row[0].strip()
        scrnum = row[1].strip()
        scrint = row[3] if row[3] != "\\N" else ""
        scrdat = _parse_date(row[4])
        scrpou_raw = row[5] if row[5] != "\\N" else "0"
        scrcon_raw = row[6] if row[6] != "\\N" else "0"

        if scrdat is None or scrdat < XVIIE_START:
            skipped_old += 1
            continue

        try:
            votes_for = int(scrpou_raw)
        except (ValueError, TypeError):
            votes_for = 0
        try:
            votes_against = int(scrcon_raw)
        except (ValueError, TypeError):
            votes_against = 0

        # Abstentions not stored directly in scr — computed from scrvot - scrpou - scrcon
        try:
            votes_total = int(row[7]) if row[7] != "\\N" else 0
        except (ValueError, TypeError):
            votes_total = 0
        votes_abstain = max(0, votes_total - votes_for - votes_against)

        # Result: adopted if pour > contre, rejected otherwise
        if votes_for > votes_against:
            result_val = "adopted"
        elif votes_against > votes_for:
            result_val = "rejected"
        else:
            result_val = "rejected"  # tied = rejected (French parliamentary procedure)

        official_id = f"SENAT_{sesann}_{scrnum}"

        result[(sesann, scrnum)] = {
            "official_id": official_id,
            "title": scrint[:4000] if scrint else "",  # guard against oversized titles
            "date": scrdat,
            "chamber": "Senat",
            "session_id": None,
            "legislature_id": None,
            "scrutin_type": "other",  # Dosleg does not categorize scrutin type
            "result": result_val,
            "votes_for": votes_for,
            "votes_against": votes_against,
            "votes_abstain": votes_abstain,
            "source_url": f"https://www.senat.fr/scrutin-public/scrutin-{sesann}-{scrnum}.html",
        }

    logger.info(
        "Parsed %d XVIIe scrutins from scr table (%d pre-XVIIe skipped, %d malformed skipped)",
        len(result),
        skipped_old,
        skipped_bad,
    )
    return result


def parse_votes(
    rows: list[list[str]],
    scrutin_keys: set[tuple[str, str]],
    actor_cache: dict[str, int],
) -> dict[tuple[str, str], list[dict]]:
    """Parse votsen COPY rows into vote dicts grouped by (sesann, scrnum).

    Only processes votes whose (sesann, scrnum) is in scrutin_keys (XVIIe filter).

    votsen column order (0-indexed):
      0:sesann 1:scrnum 2:senmat 3:posvotcod 4:titsencod 5:stavotidt
      6:senmatdel 7:votsenmar

    Returns:
        {(sesann, scrnum): [vote_dict, ...]}
    """
    grouped: dict[tuple[str, str], list[dict]] = {}
    unmatched = 0
    unknown_position = 0

    for row in rows:
        if len(row) < 4:
            continue

        sesann = row[0].strip()
        scrnum = row[1].strip()
        key = (sesann, scrnum)

        if key not in scrutin_keys:
            continue

        senmat = row[2].strip()  # character(6) — may have trailing spaces
        posvotcod = row[3].strip()

        position = _POSITION_MAP.get(posvotcod)
        if position is None:
            unknown_position += 1
            continue

        actor_id = actor_cache.get(senmat)
        if actor_id is None:
            unmatched += 1
            continue

        if key not in grouped:
            grouped[key] = []

        grouped[key].append({
            "actor_id": actor_id,
            "position": position,
            "delegation_actor_id": None,  # senmatdel tracking deferred for v1
        })

    total_votes = sum(len(v) for v in grouped.values())
    logger.info(
        "Parsed %d votes across %d scrutins (%d unmatched senmat, %d unknown position)",
        total_votes,
        len(grouped),
        unmatched,
        unknown_position,
    )
    return grouped


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def ingest_scrutins_senat(dry_run: bool = False) -> dict:
    """Download Dosleg dump, parse scrutins + votes, upsert to DB.

    Returns summary dict with counts.
    """
    logger.info("Starting Senat scrutins ingestion (dry_run=%s)", dry_run)

    # Download and parse the SQL dump
    sql_text = _download_dosleg_sql()
    logger.info("Dosleg SQL size: %.1f MB", len(sql_text) / 1_048_576)

    scr_rows = _parse_copy_block(sql_text, "scr")
    votsen_rows = _parse_copy_block(sql_text, "votsen")
    logger.info("Raw rows extracted — scr: %d, votsen: %d", len(scr_rows), len(votsen_rows))

    scrutin_map = parse_scrutins(scr_rows)

    if dry_run:
        # Dry run: parse votes with empty actor cache to count structure
        dummy_cache: dict[str, int] = {}
        votes_map = parse_votes(votsen_rows, set(scrutin_map.keys()), dummy_cache)
        logger.info(
            "[DRY-RUN] %d scrutins parsed, %d scrutins have vote data",
            len(scrutin_map),
            len(votes_map),
        )
        return {"scrutins": len(scrutin_map), "votes": 0, "unmatched": 0}

    # Live run — connect to DB
    scrutin_upsert_query = _UPSERT_SCRUTIN + " RETURNING id"
    total_scrutins = 0
    total_votes = 0
    total_unmatched = 0
    errors = 0

    with get_connection() as conn:
        actor_cache = load_actor_cache_senat(conn)

        # Parse all votes up front (in-memory — ~394k rows for XVIIe, ~30 MB)
        votes_map = parse_votes(votsen_rows, set(scrutin_map.keys()), actor_cache)
        # Count unmatched for reporting
        for row in votsen_rows:
            if len(row) >= 4:
                sesann, scrnum, senmat = row[0].strip(), row[1].strip(), row[2].strip()
                key = (sesann, scrnum)
                if key in scrutin_map and actor_cache.get(senmat) is None:
                    total_unmatched += 1

        for key, scrutin_record in tqdm(scrutin_map.items(), desc="Ingesting Senat scrutins"):
            try:
                cur = conn.execute(scrutin_upsert_query, scrutin_record)
                scrutin_id = cur.fetchone()[0]

                # Delete existing votes for idempotency
                conn.execute("DELETE FROM votes WHERE scrutin_id = %s", (scrutin_id,))

                # Insert individual votes for this scrutin
                vote_list = votes_map.get(key, [])
                for vote in vote_list:
                    conn.execute(_INSERT_VOTE, {
                        "scrutin_id": scrutin_id,
                        "actor_id": vote["actor_id"],
                        "position": vote["position"],
                        "delegation_actor_id": vote["delegation_actor_id"],
                    })

                conn.commit()
                total_scrutins += 1
                total_votes += len(vote_list)

            except Exception:
                logger.exception(
                    "Error processing scrutin SENAT_%s_%s — skipping", *key
                )
                conn.rollback()
                errors += 1
                continue

    logger.info(
        "Ingestion complete: %d scrutins, %d votes inserted, %d unmatched senmat, %d errors",
        total_scrutins,
        total_votes,
        total_unmatched,
        errors,
    )
    return {
        "scrutins": total_scrutins,
        "votes": total_votes,
        "unmatched": total_unmatched,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest Senat scrutins/votes from Dosleg PostgreSQL dump (dosleg.zip)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse dump and log counts without writing to DB",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )

    try:
        result = ingest_scrutins_senat(dry_run=args.dry_run)
        if args.dry_run:
            logger.info(
                "DRY-RUN complete — %d Senat scrutins parsed (votes not resolved without actor cache)",
                result["scrutins"],
            )
        else:
            logger.info(
                "Done — %d scrutins, %d votes in database (%d unmatched senmat)",
                result["scrutins"],
                result["votes"],
                result["unmatched"],
            )
    except Exception:
        logger.exception("Senat scrutins ingestion failed")
        raise


if __name__ == "__main__":
    main()
