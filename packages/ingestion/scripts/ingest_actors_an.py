"""Ingest active AN deputies (legislature 17) into actors + cross_references tables."""

import logging

from config import AN_OPENDATA_ZIP, AN_PHOTO_BASE, LEGISLATURE
from db import get_connection, upsert_query
from utils import download_zip_json_files, listify

logger = logging.getLogger(__name__)

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


def map_an_actor(raw: dict) -> dict:
    """Map a raw AN open-data actor JSON to our DB schema."""
    # uid may be a plain string or an XML-typed object {"#text": "PA841657", ...}
    uid_raw = raw["uid"]
    uid: str = uid_raw["#text"] if isinstance(uid_raw, dict) else uid_raw

    # Photo URL: strip "PA" prefix to get numeric ID
    numeric_id = uid.removeprefix("PA")
    photo_url = f"{AN_PHOTO_BASE}/{numeric_id}.jpg"

    # Political group: find mandat with typeOrgane == "GP", get organeRef
    mandats = listify(raw.get("mandats", {}).get("mandat"))
    political_group = None
    for m in mandats:
        if m.get("typeOrgane") == "GP":
            political_group = m.get("organes", {}).get("organeRef")
            break

    # Constituency from ASSEMBLEE mandate
    constituency = None
    for m in mandats:
        if m.get("typeOrgane") == "ASSEMBLEE":
            election = m.get("election", {})
            lieu = election.get("lieu", {})
            departement = lieu.get("departement")
            num_circo = lieu.get("numCirco")
            if departement and num_circo:
                constituency = f"{departement} ({num_circo})"
            elif departement:
                constituency = departement
            break

    prenom = raw["etatCivil"]["ident"]["prenom"]
    nom = raw["etatCivil"]["ident"]["nom"]

    return {
        "official_id": uid,
        "first_name": prenom,
        "last_name": nom,
        "full_name": f"{prenom} {nom}".strip(),
        "political_group": political_group,
        "photo_url": photo_url,
        "constituency": constituency,
        "is_active": True,
        "actor_type": "deputy",
        "chamber": "AN",
        "legislature": LEGISLATURE,
    }


def ingest_actors_an() -> tuple[int, int]:
    """Download, map, and upsert all AN deputies. Returns (actor_count, xref_count)."""
    # Download ZIP and extract actor JSON files (PA*.json, not organs)
    all_files = download_zip_json_files(AN_OPENDATA_ZIP)
    actor_files = {k: v for k, v in all_files.items() if "/acteur/PA" in k}
    logger.info("Found %d actor files in ZIP", len(actor_files))

    # Each file has {"acteur": {...}} wrapper — unwrap before mapping
    actors = [map_an_actor(v["acteur"]) for v in actor_files.values()]
    logger.info("Mapped %d AN actors", len(actors))

    actor_query = upsert_query(
        table="actors",
        columns=ACTOR_COLUMNS,
        conflict_column="official_id",
        has_updated_at=True,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Seed legislature 17 first
            cur.execute(
                """
                INSERT INTO legislatures (number, start_date, chamber)
                VALUES (17, '2024-07-08', 'AN')
                ON CONFLICT (number) DO NOTHING
                """,
            )

            # Upsert all actors
            cur.executemany(actor_query, actors)
            logger.info("Upserted %d AN actors", len(actors))

            # Fetch actor ids for cross_references
            official_ids = [a["official_id"] for a in actors]
            cur.execute(
                "SELECT id, official_id FROM actors WHERE chamber='AN' AND official_id = ANY(%s)",
                (official_ids,),
            )
            id_map = {row[1]: row[0] for row in cur.fetchall()}

            # Insert cross_references: source_type='PA', source_id=official_id
            xref_count = 0
            for official_id, actor_id in id_map.items():
                cur.execute(
                    """
                    INSERT INTO cross_references (actor_id, source_type, source_id)
                    VALUES (%s, 'PA', %s)
                    ON CONFLICT (actor_id, source_type, source_id) DO NOTHING
                    """,
                    (actor_id, official_id),
                )
                xref_count += cur.rowcount

        conn.commit()

    logger.info(
        "Upserted %d AN deputies, %d cross-references created",
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
        actor_count, xref_count = ingest_actors_an()
        logger.info("Done — %d AN deputies, %d cross-references in database", actor_count, xref_count)
    except Exception:
        logger.exception("AN actor ingestion failed")
        raise
