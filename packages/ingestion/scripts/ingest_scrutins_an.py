"""Ingest AN scrutins (public votes) + individual vote positions into scrutins + votes tables.

Downloads Scrutins.json.zip from data.assemblee-nationale.fr, parses each per-scrutin
JSON file, upserts the scrutin record, and inserts individual vote positions per deputy.

Actor matching uses cross_references WHERE source_type = 'PA' — reliable PA-based matching
established in Phase 10 (ingest_actors_an.py populates cross_references).

Idempotency:
  - scrutins upserted by official_id (ON CONFLICT DO UPDATE)
  - votes: DELETE + INSERT per scrutin_id (same pattern as interventions in Phase 11)

Usage:
    python ingest_scrutins_an.py
    python ingest_scrutins_an.py --dry-run   # Parse only, no DB writes
"""

import argparse
import logging
from datetime import date

from tqdm import tqdm

from config import AN_SCRUTINS_ZIP
from db import get_connection, upsert_query
from utils import download_zip_json_files, listify

logger = logging.getLogger(__name__)

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

VOTE_COLUMNS = ["scrutin_id", "actor_id", "position", "delegation_actor_id"]

# Pre-built INSERT query for votes (executed per vote row)
_INSERT_VOTE = (
    "INSERT INTO votes (scrutin_id, actor_id, position, delegation_actor_id) "
    "VALUES (%(scrutin_id)s, %(actor_id)s, %(position)s, %(delegation_actor_id)s)"
)

# Pre-built UPSERT query for scrutins (appended RETURNING id at call site)
_UPSERT_SCRUTIN = upsert_query("scrutins", SCRUTIN_COLUMNS, "official_id")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decode_text(v) -> str:
    """Decode psycopg3 binary-protocol text column to Python str.

    psycopg3 in binary mode can return text columns as bytes. Always coerce to str.
    """
    if isinstance(v, (bytes, memoryview)):
        return bytes(v).decode("utf-8")
    return str(v)


def load_actor_cache_an(conn) -> dict[str, int]:
    """Return {source_id: actor_id} from cross_references WHERE source_type = 'PA'.

    Keys are PA-prefixed IDs (e.g. 'PA841657'), values are DB integer actor ids.
    This is the reliable, collision-free matching path for AN deputies.
    """
    cur = conn.execute(
        "SELECT source_id, actor_id FROM cross_references WHERE source_type = 'PA'"
    )
    # _decode_text handles psycopg3 binary protocol returning text columns as bytes
    cache = {_decode_text(row[0]): row[1] for row in cur.fetchall()}
    logger.info("Loaded %d PA actor references from cross_references", len(cache))
    return cache


def map_scrutin_type(code: str) -> str:
    """Map AN codeTypeVote to schema values (ordinary | solemn | other)."""
    if code == "SPS":
        return "solemn"
    if code == "SPO":
        return "ordinary"
    return "other"


def map_result(code: str) -> str:
    """Map AN sort.code to schema values (adopted | rejected | raw code)."""
    lower = code.lower()
    if "adopt" in lower:
        return "adopted"
    if "rejet" in lower:
        return "rejected"
    return code


def build_scrutin_record(scrutin: dict) -> dict:
    """Extract and map fields from a raw AN scrutin JSON object."""
    type_vote = scrutin.get("typeVote", {})
    sort = scrutin.get("sort", {})
    synthese = scrutin.get("syntheseVote", {})

    # Parse date: dateScrutin is 'YYYY-MM-DD' string
    date_str = scrutin.get("dateScrutin", "")
    try:
        parsed_date = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        logger.warning("Could not parse dateScrutin '%s' for scrutin %s", date_str, scrutin.get("uid"))
        parsed_date = None

    # Vote counts: actual JSON uses syntheseVote.decompte.{pour,contre,abstentions}
    # (not syntheseVote.pour.nbrVoix as some documentation suggests)
    decompte = synthese.get("decompte", {})
    try:
        votes_for = int(decompte.get("pour", 0))
    except (ValueError, TypeError):
        votes_for = 0
    try:
        votes_against = int(decompte.get("contre", 0))
    except (ValueError, TypeError):
        votes_against = 0
    try:
        votes_abstain = int(decompte.get("abstentions", 0))
    except (ValueError, TypeError):
        votes_abstain = 0

    uid = scrutin.get("uid", "")
    return {
        "official_id": uid,
        "title": scrutin.get("titre", ""),
        "date": parsed_date,
        "chamber": "AN",
        "session_id": None,  # Session-to-debate linkage deferred: seanceRef lookup non-trivial
        "legislature_id": None,  # Legislatures not yet used for FK resolution
        "scrutin_type": map_scrutin_type(type_vote.get("codeTypeVote", "")),
        "result": map_result(sort.get("code", "")),
        "votes_for": votes_for,
        "votes_against": votes_against,
        "votes_abstain": votes_abstain,
        "source_url": f"https://www.assemblee-nationale.fr/dyn/17/scrutins/{uid}",
    }


def extract_votes(scrutin: dict, actor_cache: dict[str, int]) -> tuple[list[dict], int]:
    """Extract all individual vote positions from ventilationVotes.

    Navigates: ventilationVotes.organe.groupes.groupe (list or single dict).
    For each group iterates: pours / contres / abstentions / nonVotants sections.

    Returns:
        (vote_dicts, unmatched_count) — list of vote records ready for DB insert,
        and a count of acteurRef values not found in the actor cache.
    """
    votes: list[dict] = []
    unmatched = 0

    try:
        ventilation = scrutin.get("ventilationVotes", {})
        organe = ventilation.get("organe", {})
        groupes_raw = organe.get("groupes", {}).get("groupe")
    except AttributeError:
        logger.warning("Scrutin %s has no ventilationVotes structure", scrutin.get("uid"))
        return votes, unmatched

    groupes = listify(groupes_raw)

    position_keys = [
        ("pours", "for"),
        ("contres", "against"),
        ("abstentions", "abstain"),
        ("nonVotants", "absent"),
    ]

    for groupe in groupes:
        try:
            decompte = groupe.get("vote", {}).get("decompteNominatif", {})
        except AttributeError:
            continue

        for section_key, position_val in position_keys:
            section = decompte.get(section_key)
            if not section:
                continue

            votants_raw = section.get("votant")
            if not votants_raw:
                continue

            votants = listify(votants_raw)
            for votant in votants:
                acteur_ref = votant.get("acteurRef")
                if not acteur_ref:
                    continue

                actor_id = actor_cache.get(acteur_ref)
                if actor_id is None:
                    unmatched += 1
                    continue

                # parDelegation is a string "true"/"false" in AN JSON — NOT a bool
                par_delegation = votant.get("parDelegation") == "true"

                votes.append({
                    "actor_id": actor_id,
                    "position": position_val,
                    # Delegation tracking deferred for v1: delegation_actor_id = None
                    "delegation_actor_id": None,
                    "_par_delegation": par_delegation,  # kept for future use
                })

    return votes, unmatched


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def ingest_scrutins_an(dry_run: bool = False) -> dict:
    """Download ZIP, parse scrutin files, upsert scrutins + insert votes.

    Returns summary dict with counts for logging.
    """
    logger.info("Starting AN scrutins ingestion (dry_run=%s)", dry_run)

    # Download all JSON files from the scrutins ZIP
    all_files = download_zip_json_files(AN_SCRUTINS_ZIP)
    scrutin_files = {k: v for k, v in all_files.items() if k.endswith(".json") and "scrutin" in v}
    logger.info("Found %d scrutin JSON files in ZIP", len(scrutin_files))

    if dry_run:
        # Dry-run: parse only, count votes, no DB writes
        total_scrutins = 0
        total_votes = 0
        total_unmatched = 0

        # Build a dummy actor cache for structure validation
        dummy_cache: dict[str, int] = {}
        for data in tqdm(scrutin_files.values(), desc="Parsing (dry-run)"):
            scrutin = data["scrutin"]
            build_scrutin_record(scrutin)
            vote_list, unmatched = extract_votes(scrutin, dummy_cache)
            total_scrutins += 1
            total_votes += len(vote_list)
            total_unmatched += unmatched

        logger.info(
            "[DRY-RUN] Parsed %d scrutins — votes would require actor cache to count accurately",
            total_scrutins,
        )
        return {
            "scrutins": total_scrutins,
            "votes": total_votes,
            "unmatched": total_unmatched,
        }

    # Live run — connect to DB
    total_scrutins = 0
    total_votes = 0
    total_unmatched = 0
    errors = 0

    scrutin_upsert_query = _UPSERT_SCRUTIN + " RETURNING id"

    with get_connection() as conn:
        actor_cache = load_actor_cache_an(conn)

        for filename, data in tqdm(scrutin_files.items(), desc="Ingesting scrutins"):
            try:
                scrutin = data["scrutin"]
                record = build_scrutin_record(scrutin)

                # Upsert scrutin row — get back the DB id
                cur = conn.execute(scrutin_upsert_query, record)
                scrutin_id = cur.fetchone()[0]

                # Delete existing votes for this scrutin (idempotent)
                conn.execute("DELETE FROM votes WHERE scrutin_id = %s", (scrutin_id,))

                # Extract all individual vote positions
                vote_list, unmatched = extract_votes(scrutin, actor_cache)
                total_unmatched += unmatched

                # Bulk insert votes
                for vote in vote_list:
                    vote_row = {
                        "scrutin_id": scrutin_id,
                        "actor_id": vote["actor_id"],
                        "position": vote["position"],
                        "delegation_actor_id": vote["delegation_actor_id"],
                    }
                    conn.execute(_INSERT_VOTE, vote_row)

                # Commit once per scrutin (not per vote — performance)
                conn.commit()

                total_scrutins += 1
                total_votes += len(vote_list)

            except Exception:
                logger.exception("Error processing scrutin file %s — skipping", filename)
                conn.rollback()
                errors += 1
                continue

    logger.info(
        "Ingestion complete: %d scrutins, %d votes inserted, %d unmatched acteurRef, %d errors",
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


def main():
    parser = argparse.ArgumentParser(
        description="Ingest AN scrutins/votes from Scrutins.json.zip"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse ZIP and log counts without writing to DB",
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )

    try:
        result = ingest_scrutins_an(dry_run=args.dry_run)
        if args.dry_run:
            logger.info(
                "DRY-RUN complete — %d scrutins parsed (votes not counted without actor cache)",
                result["scrutins"],
            )
        else:
            logger.info(
                "Done — %d scrutins, %d votes in database (%d unmatched acteurRef)",
                result["scrutins"],
                result["votes"],
                result["unmatched"],
            )
    except Exception:
        logger.exception("AN scrutins ingestion failed")
        raise


if __name__ == "__main__":
    main()
