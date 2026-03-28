"""Ingest AN organs (commissions permanentes, groupes politiques, delegations) into organs table.

Source: AMO10 ZIP (same archive as actors) — files matching json/organe/PO*.json.
Also resolves actors.political_group from PO organeRef to human-readable name.
"""

import logging

from config import AN_OPENDATA_ZIP
from db import get_connection, upsert_query
from utils import download_zip_json_files

logger = logging.getLogger(__name__)

# Map AN codeType to our schema organ_type
ORGAN_TYPE_MAP = {
    "GP": "group",
    "COMPER": "commission",
    "DELEG": "delegation",
    "OFFPAR": "other",
    "BUREAU": "other",
    "ASSEMBLEE": "other",
    "CMP": "other",
    "COMNL": "commission",
    "CNPS": "other",
    "CNPE": "other",
    "GA": "other",
    "GE": "other",
    "GROUPEAMITIE": "other",
}

# Only ingest these types — skip meta-organs (ASSEMBLEE, BUREAU, OFFPAR, etc.)
ORGAN_TYPE_FILTER = {"GP", "COMPER", "DELEG"}

# Columns to upsert — never includes 'id' (GENERATED ALWAYS AS IDENTITY)
# organs table has created_at only (no updated_at)
ORGAN_COLUMNS = [
    "official_id",
    "name",
    "short_name",
    "organ_type",
    "chamber",
    "legislature_id",
    "parent_organ_id",
    "start_date",
    "end_date",
]


def map_an_organ(raw: dict) -> dict | None:
    """Map a raw AN open-data organ JSON to our DB schema.

    Returns None for organs that should be skipped (not in ORGAN_TYPE_FILTER).
    """
    code_type = raw.get("codeType", "")
    if code_type not in ORGAN_TYPE_FILTER:
        return None

    # viMoDe contains date fields
    vi_mo_de = raw.get("viMoDe", {})

    return {
        "official_id": raw["uid"],
        "name": raw.get("libelle", ""),
        "short_name": raw.get("libelleAbrege") or raw.get("libelleAbrev"),
        "organ_type": ORGAN_TYPE_MAP.get(code_type, "other"),
        "chamber": "AN",
        "legislature_id": None,  # would require a lookup — keep nullable for simplicity
        "parent_organ_id": None,  # no FK constraint, skip resolution
        "start_date": vi_mo_de.get("dateDebut"),
        "end_date": vi_mo_de.get("dateFin"),
    }


def ingest_organs_an() -> tuple[int, int]:
    """Download, map, and upsert all AN organs. Returns (organ_count, resolved_actors)."""
    # Download ZIP and extract organ JSON files (PO*.json, not actors)
    all_files = download_zip_json_files(AN_OPENDATA_ZIP)
    organ_files = {k: v for k, v in all_files.items() if "/organe/PO" in k}
    logger.info("Found %d organ files in ZIP", len(organ_files))

    # Each file has {"organe": {...}} wrapper — unwrap before mapping
    organs = []
    skipped = 0
    for v in organ_files.values():
        raw = v.get("organe", v)  # some files may not have wrapper
        mapped = map_an_organ(raw)
        if mapped is not None:
            organs.append(mapped)
        else:
            skipped += 1

    logger.info("Mapped %d organs (%d skipped, not in filter)", len(organs), skipped)

    organ_query = upsert_query(
        table="organs",
        columns=ORGAN_COLUMNS,
        conflict_column="official_id",
        has_updated_at=False,  # organs table has no updated_at column
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Upsert all organs
            cur.executemany(organ_query, organs)
            logger.info("Upserted %d AN organs", len(organs))

            # Resolve actors.political_group from PO organeRef to human-readable short_name
            # AN actors store e.g. "PO834720" in political_group — replace with group short name
            cur.execute(
                """
                UPDATE actors
                SET political_group = o.short_name
                FROM organs o
                WHERE actors.political_group = o.official_id
                  AND actors.chamber = 'AN'
                  AND o.organ_type = 'group'
                """
            )
            resolved_actors = cur.rowcount
            logger.info("Resolved political_group for %d AN actors (PO ref → name)", resolved_actors)

        conn.commit()

    logger.info("Done — %d AN organs upserted, %d actors resolved", len(organs), resolved_actors)
    return len(organs), resolved_actors


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )
    try:
        organ_count, resolved = ingest_organs_an()
        logger.info("Done — %d AN organs in database, %d actors' political_group resolved", organ_count, resolved)
    except Exception:
        logger.exception("AN organ ingestion failed")
        raise
