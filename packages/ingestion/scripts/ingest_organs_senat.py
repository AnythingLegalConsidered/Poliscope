"""Ingest Senat organs (commissions permanentes, delegations, groupes politiques) into organs table.

Source: senat.fr API senateurs.json — extract unique organs from all senators' organismes[] arrays
and political groups from each senator's groupe field.
"""

import logging
import re

import httpx

from config import REQUEST_DELAY, SENAT_API_BASE
from db import get_connection, upsert_query
from utils import rate_limit

logger = logging.getLogger(__name__)

# Map Senat organ type strings to our schema organ_type
SENAT_ORGAN_TYPE_MAP = {
    "COMMISSION": "commission",
    "ETUDE": "other",
    "GIA": "other",
    "DELEGATION": "delegation",
    "OFFICE": "other",
}

# Only ingest these organism types — skip ETUDE, GIA, OFFICE (out of Phase 10 scope)
ORGAN_TYPE_FILTER = {"COMMISSION", "DELEGATION"}

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


def _slugify(text: str) -> str:
    """Create a stable slug from a string for use in official_id."""
    # Lowercase, replace accented chars, replace non-alphanumeric with underscore
    text = text.lower().strip()
    # Replace common accented characters
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c",
        " ": "_", "-": "_", "'": "_", "/": "_",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Remove any remaining non-alphanumeric characters except underscore
    text = re.sub(r"[^a-z0-9_]", "", text)
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def map_senat_organ(code: str, type_str: str, libelle: str) -> dict | None:
    """Map a Senat organ (code, type, libelle) to our DB schema.

    Returns None for organs not in ORGAN_TYPE_FILTER.
    """
    if type_str not in ORGAN_TYPE_FILTER:
        return None

    return {
        "official_id": f"SENAT_{code}",  # prefix to avoid collision with AN PO IDs
        "name": libelle,
        "short_name": code,  # short identifier
        "organ_type": SENAT_ORGAN_TYPE_MAP.get(type_str, "other"),
        "chamber": "Senat",
        "legislature_id": None,  # not available in API
        "parent_organ_id": None,
        "start_date": None,  # not available in API
        "end_date": None,
    }


def map_senat_political_group(libelle: str) -> dict:
    """Map a Senat political group name to our DB schema."""
    slug = _slugify(libelle)
    return {
        "official_id": f"SENAT_GP_{slug}",  # stable ID from group name
        "name": libelle,
        "short_name": libelle,  # for groups, libelle IS the short label (e.g. "RDPI", "SER")
        "organ_type": "group",
        "chamber": "Senat",
        "legislature_id": None,
        "parent_organ_id": None,
        "start_date": None,
        "end_date": None,
    }


def fetch_senators() -> list[dict]:
    """Fetch all active senators from senat.fr API. Returns a list."""
    url = f"{SENAT_API_BASE}/senateurs.json"
    logger.info("GET %s", url)
    with httpx.Client(timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    rate_limit()
    # API returns a plain list (not wrapped in a dict)
    return data if isinstance(data, list) else data.get("senateurs", [])


def ingest_organs_senat() -> int:
    """Fetch, extract unique organs, and upsert. Returns organ_count."""
    raw_senators = fetch_senators()
    logger.info("Fetched %d senators from senat.fr API", len(raw_senators))

    # Collect unique organs by official_id
    organs_by_id: dict[str, dict] = {}

    # 1. Extract organismes[] from each senator
    for senator in raw_senators:
        for org in senator.get("organismes") or []:
            code = org.get("code")
            type_str = org.get("type", "")
            libelle = org.get("libelle", "")
            if not code:
                continue
            mapped = map_senat_organ(code, type_str, libelle)
            if mapped is not None:
                official_id = mapped["official_id"]
                if official_id not in organs_by_id:
                    organs_by_id[official_id] = mapped

    # 2. Extract political groups from each senator's groupe field
    for senator in raw_senators:
        groupe = senator.get("groupe")
        if not groupe:
            continue
        libelle = groupe.get("libelle")
        if not libelle:
            continue
        mapped = map_senat_political_group(libelle)
        official_id = mapped["official_id"]
        if official_id not in organs_by_id:
            organs_by_id[official_id] = mapped

    organs = list(organs_by_id.values())
    logger.info("Collected %d unique Senat organs", len(organs))

    organ_query = upsert_query(
        table="organs",
        columns=ORGAN_COLUMNS,
        conflict_column="official_id",
        has_updated_at=False,  # organs table has no updated_at column
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(organ_query, organs)
            logger.info("Upserted %d Senat organs", len(organs))
        conn.commit()

    logger.info("Done — %d Senat organs in database", len(organs))
    return len(organs)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )
    try:
        organ_count = ingest_organs_senat()
        logger.info("Done — %d Senat organs in database", organ_count)
    except Exception:
        logger.exception("Senat organ ingestion failed")
        raise
