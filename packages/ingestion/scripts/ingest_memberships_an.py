"""Ingest AN actor-organ memberships from AMO10 ZIP mandats into actor_organs table.

Source: AMO10 ZIP (same archive as actors/organs) — PA*.json actor files.
For each actor, iterate mandats with typeOrgane in {GP, COMPER, DELEG} and upsert
into actor_organs with FK resolution from actors + organs tables.

Known limitation: Senat memberships are NOT ingested here.
senateurs.json provides organismes[] but with NO start_date/end_date.
Senat membership ingestion deferred — requires scraping individual senator pages
or a different API endpoint providing membership dates.
"""

import logging

from config import AN_OPENDATA_ZIP
from db import get_connection
from utils import download_zip_json_files, listify

logger = logging.getLogger(__name__)

# Only process these mandat types — same filter as organs ingestion
MEMBERSHIP_TYPE_FILTER = {"GP", "COMPER", "DELEG"}

# Map codeQualite values to normalized role strings
ROLE_MAP = {
    "Membre": "membre",
    "Président": "president",
    "President": "president",
    "Vice-Président": "vice-president",
    "Vice-President": "vice-president",
    "Co-Rapporteur": "co-rapporteur",
    "Rapporteur": "rapporteur",
    "Secrétaire": "secretaire",
    "Secretaire": "secretaire",
    "Questeur": "questeur",
    "Président délégué": "president-delegue",
}


def extract_memberships(actor_files: dict) -> list[dict]:
    """Extract membership dicts from all actor JSON files.

    Returns a list of dicts with keys:
    actor_official_id, organ_official_id, role, start_date, end_date
    """
    memberships = []
    total_mandats = 0

    for _filename, file_data in actor_files.items():
        actor = file_data.get("acteur", file_data)

        # Extract actor official_id — may be a plain string or XML-typed object
        uid_raw = actor.get("uid", "")
        uid: str = uid_raw["#text"] if isinstance(uid_raw, dict) else uid_raw
        if not uid:
            continue

        mandats = listify(actor.get("mandats", {}).get("mandat"))

        for mandat in mandats:
            type_organe = mandat.get("typeOrgane", "")
            if type_organe not in MEMBERSHIP_TYPE_FILTER:
                continue

            total_mandats += 1

            # Get organ reference — organes.organeRef may be a string or dict
            organes = mandat.get("organes", {})
            organ_ref_raw = organes.get("organeRef", "")
            organ_ref: str = organ_ref_raw["#text"] if isinstance(organ_ref_raw, dict) else organ_ref_raw
            if not organ_ref:
                continue

            # Dates at mandat root level
            start_date = mandat.get("dateDebut") or None
            end_date = mandat.get("dateFin") or None

            # Role from infosQualite.codeQualite — default to "membre"
            infos = mandat.get("infosQualite", {})
            code_qualite = infos.get("codeQualite", "")
            role = ROLE_MAP.get(code_qualite, "membre")

            memberships.append({
                "actor_official_id": uid,
                "organ_official_id": organ_ref,
                "role": role,
                "start_date": start_date,
                "end_date": end_date,
            })

    logger.info("Extracted %d memberships (%d actor files processed)", len(memberships), len(actor_files))
    return memberships


def resolve_fks(memberships: list[dict], conn) -> list[dict]:
    """Resolve actor_official_id and organ_official_id to integer FKs.

    Returns a list of dicts ready for INSERT with keys:
    actor_id, organ_id, role, start_date, end_date
    """
    def _decode(v) -> str:
        """Decode bytes -> str if psycopg3 binary protocol returns text as bytes."""
        if isinstance(v, (bytes, memoryview)):
            return bytes(v).decode("utf-8")
        return str(v)

    with conn.cursor() as cur:
        # Build actor_id lookup: official_id -> id (AN chamber only)
        cur.execute("SELECT id, official_id FROM actors WHERE chamber='AN'")
        actor_id_map = {_decode(row[1]): row[0] for row in cur.fetchall()}

        # Build organ_id lookup: official_id -> id (AN chamber only)
        cur.execute("SELECT id, official_id FROM organs WHERE chamber='AN'")
        organ_id_map = {_decode(row[1]): row[0] for row in cur.fetchall()}

    logger.info("Loaded %d AN actors and %d AN organs for FK resolution", len(actor_id_map), len(organ_id_map))

    resolved = []
    skipped_actor = 0
    skipped_organ = 0

    for m in memberships:
        actor_id = actor_id_map.get(m["actor_official_id"])
        if actor_id is None:
            skipped_actor += 1
            continue

        organ_id = organ_id_map.get(m["organ_official_id"])
        if organ_id is None:
            skipped_organ += 1
            logger.debug("Organ not found: %s (actor %s)", m["organ_official_id"], m["actor_official_id"])
            continue

        resolved.append({
            "actor_id": actor_id,
            "organ_id": organ_id,
            "role": m["role"],
            "start_date": m["start_date"],
            "end_date": m["end_date"],
        })

    logger.info(
        "FK resolution: %d resolved, %d skipped (actor not found: %d, organ not found: %d)",
        len(resolved), skipped_actor + skipped_organ, skipped_actor, skipped_organ,
    )
    return resolved


# Custom upsert query — can't use upsert_query() helper (only supports single conflict column)
MEMBERSHIP_UPSERT = """
INSERT INTO actor_organs (actor_id, organ_id, role, start_date, end_date)
VALUES (%(actor_id)s, %(organ_id)s, %(role)s, %(start_date)s, %(end_date)s)
ON CONFLICT (actor_id, organ_id) DO UPDATE SET
  role = EXCLUDED.role,
  start_date = EXCLUDED.start_date,
  end_date = EXCLUDED.end_date
"""


def ingest_memberships_an() -> int:
    """Download, extract mandats, resolve FKs, and upsert AN memberships.

    Returns count of rows upserted.
    """
    # Download ZIP and extract actor JSON files (PA*.json only)
    all_files = download_zip_json_files(AN_OPENDATA_ZIP)
    actor_files = {k: v for k, v in all_files.items() if "/acteur/PA" in k}
    logger.info("Found %d actor files in ZIP", len(actor_files))

    # Extract membership dicts from actor mandats
    memberships = extract_memberships(actor_files)

    if not memberships:
        logger.warning("No memberships extracted — nothing to upsert")
        return 0

    with get_connection() as conn:
        # Resolve official_ids to integer FKs
        resolved = resolve_fks(memberships, conn)

        if not resolved:
            logger.warning("No memberships survived FK resolution — check actors and organs tables")
            return 0

        with conn.cursor() as cur:
            cur.executemany(MEMBERSHIP_UPSERT, resolved)
            logger.info("Upserted %d actor_organs rows", len(resolved))

        conn.commit()

    return len(resolved)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=_logging.INFO,
    )
    try:
        count = ingest_memberships_an()
        logger.info("Done — %d AN memberships in actor_organs table", count)
    except Exception:
        logger.exception("AN membership ingestion failed")
        raise
