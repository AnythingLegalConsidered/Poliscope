"""Ingest active senators from senat.fr API into actors + cross_references tables."""

import logging

import httpx

from config import REQUEST_DELAY, SENAT_API_BASE
from db import get_connection, upsert_query
from utils import rate_limit

logger = logging.getLogger(__name__)

# Base URL for senator photos (urlAvatar is relative)
SENAT_BASE: str = "https://www.senat.fr"

# Columns to upsert — never includes 'id' (GENERATED ALWAYS AS IDENTITY)
ACTOR_COLUMNS = [
    "official_id",
    "first_name",
    "last_name",
    "full_name",
    "political_group",
    "photo_url",
    "constituency",
    "is_active",
    "actor_type",
    "chamber",
    "legislature",
]


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


def map_senat_actor(raw: dict) -> dict:
    """Map a raw senat.fr senator dict to our DB schema."""
    matricule: str = raw["matricule"]

    prenom = raw.get("prenom", "")
    nom = raw.get("nom", "")

    # Political group: raw["groupe"]["libelle"] if present
    groupe = raw.get("groupe")
    political_group = groupe.get("libelle") if groupe else None

    # Photo URL: prepend base URL since urlAvatar is relative
    url_avatar = raw.get("urlAvatar")
    photo_url = f"{SENAT_BASE}{url_avatar}" if url_avatar else None

    # Constituency: raw["circonscription"]["libelle"] if present
    circo = raw.get("circonscription")
    constituency = circo.get("libelle") if circo else None

    return {
        "official_id": matricule,
        "first_name": prenom,
        "last_name": nom,
        "full_name": f"{prenom} {nom}".strip(),
        "political_group": political_group,
        "photo_url": photo_url,
        "constituency": constituency,
        "is_active": True,
        "actor_type": "senator",
        "chamber": "Senat",
        "legislature": None,  # Senate has no discrete legislature
    }


def ingest_actors_senat() -> tuple[int, int]:
    """Fetch, map, and upsert all senators. Returns (actor_count, xref_count)."""
    raw_senators = fetch_senators()
    logger.info("Fetched %d senators from senat.fr API", len(raw_senators))

    actors = [map_senat_actor(s) for s in raw_senators]
    logger.info("Mapped %d senators", len(actors))

    actor_query = upsert_query(
        table="actors",
        columns=ACTOR_COLUMNS,
        conflict_column="official_id",
        has_updated_at=True,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Upsert all senators
            cur.executemany(actor_query, actors)
            logger.info("Upserted %d senators", len(actors))

            # Fetch actor ids for cross_references
            official_ids = [a["official_id"] for a in actors]
            cur.execute(
                "SELECT id, official_id FROM actors WHERE chamber='Senat' AND official_id = ANY(%s)",
                (official_ids,),
            )
            id_map = {row[1]: row[0] for row in cur.fetchall()}

            # Insert cross_references: source_type='senat', source_id=matricule
            xref_count = 0
            for official_id, actor_id in id_map.items():
                cur.execute(
                    """
                    INSERT INTO cross_references (actor_id, source_type, source_id)
                    VALUES (%s, 'senat', %s)
                    ON CONFLICT (actor_id, source_type, source_id) DO NOTHING
                    """,
                    (actor_id, official_id),
                )
                xref_count += cur.rowcount

        conn.commit()

    logger.info(
        "Upserted %d senators, %d cross-references created",
        len(actors),
        xref_count,
    )
    return len(actors), xref_count


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )
    try:
        actor_count, xref_count = ingest_actors_senat()
        logger.info("Done — %d senators, %d cross-references in database", actor_count, xref_count)
    except Exception:
        logger.exception("Senat actor ingestion failed")
        raise
