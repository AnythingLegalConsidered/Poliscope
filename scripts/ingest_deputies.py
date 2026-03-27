"""Ingest deputies from nosdeputes.fr into the Poliscope database."""

import logging

from config import NOSDEPUTES_BASE
from db import get_connection, upsert_query
from utils import fetch_json

logger = logging.getLogger(__name__)

# Columns to upsert (never includes 'id' — GENERATED ALWAYS AS IDENTITY)
DEPUTY_COLUMNS = [
    "official_id",
    "first_name",
    "last_name",
    "full_name",
    "political_group",
    "photo_url",
    "constituency",
    "is_active",
]


def fetch_deputies() -> list[dict]:
    """Fetch all deputies (current + former) from nosdeputes.fr."""
    url = f"{NOSDEPUTES_BASE}/deputes/json"
    data = fetch_json(url)
    return [entry["depute"] for entry in data.get("deputes", [])]


def map_deputy(raw: dict) -> dict:
    """Map a raw nosdeputes.fr deputy dict to our DB schema."""
    # official_id: prefer id_an (Assemblee Nationale ID), fallback to id
    official_id = str(raw.get("id_an") or raw["id"])

    # Photo URL from slug
    slug = raw.get("slug")
    photo_url = f"{NOSDEPUTES_BASE}/depute/photo/{slug}/120" if slug else None

    # Constituency: "nom_circo (num_circo)"
    nom_circo = raw.get("nom_circo")
    num_circo = raw.get("num_circo")
    constituency = f"{nom_circo} ({num_circo})" if nom_circo and num_circo else None

    # Active if mandat_fin is None or empty
    mandat_fin = raw.get("mandat_fin")
    is_active = not mandat_fin  # None or "" => True

    return {
        "official_id": official_id,
        "first_name": raw.get("prenom", ""),
        "last_name": raw.get("nom_de_famille", ""),
        "full_name": raw.get("nom", ""),
        "political_group": raw.get("groupe_sigle"),
        "photo_url": photo_url,
        "constituency": constituency,
        "is_active": is_active,
    }


def ingest_deputies() -> int:
    """Fetch, map, and upsert all deputies. Returns count."""
    raw_deputies = fetch_deputies()
    logger.info("Fetched %d deputies from nosdeputes.fr", len(raw_deputies))

    query = upsert_query(
        table="deputies",
        columns=DEPUTY_COLUMNS,
        conflict_column="official_id",
        has_updated_at=True,
    )

    count = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for raw in raw_deputies:
                deputy = map_deputy(raw)
                cur.execute(query, deputy)
                count += 1
        conn.commit()

    logger.info("Upserted %d deputies", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )
    try:
        total = ingest_deputies()
        logger.info("Done — %d deputies in database", total)
    except Exception:
        logger.exception("Deputy ingestion failed")
        raise
